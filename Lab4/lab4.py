import time
from pathlib import Path

import numpy as np


VARIANT = 18
BIT_DEPTH = 16
MAX_VALUE = 2**BIT_DEPTH - 1

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_orca_raster_8bit() -> np.ndarray:
    """
    Базове 8-бітне зображення з попередньої лабораторної:
    темний силует касатки на світлому фоні.
    """
    pattern = [
        "000000000000000001110000000000",
        "000000000000000011110000000000",
        "000000000000000111100000000000",
        "000000000000001111100000000000",
        "000000000000001111100000000000",
        "000000000111111111100000000000",
        "000011111111111111100000000000",
        "000111111111111111110000000000",
        "011111111111111111111100000000",
        "011111111111111111111110000000",
        "111111111111111111111111000000",
        "111111111111111111111111100000",
        "111111111111111111111111100000",
        "011111111111111111111111110000",
        "000111111111111111111111111000",
        "000001111111111111111111111000",
        "000000011111111111111111111000",
        "000000000111111111111111111000",
        "000000000001111111111111111100",
        "000000000000000000001111111100",
        "000000000000000000000111111100",
        "000000000000000000000011111110",
        "000000000000000000000011111111",
        "000000000000000000000011100111",
        "000000000000000000000011000011",
    ]

    raster = np.zeros((25, 30), dtype=np.uint8)

    for y, row in enumerate(pattern):
        for x, value in enumerate(row):
            raster[y, x] = 35 if value == "1" else 220

    return raster


def upscale_nearest(image: np.ndarray, factor: int) -> np.ndarray:
    """
    Масштабування зображення методом найближчого сусіда.
    Це потрібно, щоб результат був зручнішим для перегляду.
    """
    return np.repeat(np.repeat(image, factor, axis=0), factor, axis=1)


def make_16bit_noisy_image(image_8bit: np.ndarray, seed: int = 18) -> np.ndarray:
    """
    Перетворює 8-бітне grayscale-зображення у 16-бітне
    та додає шум, щоб було що знешумлювати.
    """
    rng = np.random.default_rng(seed)

    image = image_8bit.astype(np.float64) / 255.0
    image_16 = image * MAX_VALUE

    gaussian_noise = rng.normal(loc=0.0, scale=3500.0, size=image_16.shape)
    noisy = image_16 + gaussian_noise

    # Додаємо випадкові "соляні" та "перцеві" пікселі
    random_map = rng.random(image_16.shape)
    noisy[random_map < 0.015] = 0
    noisy[random_map > 0.985] = MAX_VALUE

    return np.clip(noisy, 0, MAX_VALUE).astype(np.uint16)


def segment(image: np.ndarray, threshold: int, variant: int) -> np.ndarray:
    """
    Сегментація за threshold.
    Для парного варіанта активними є значення <= threshold.
    Для непарного — значення > threshold.
    """
    if variant % 2 == 0:
        return image <= threshold
    return image > threshold


def erode(mask: np.ndarray) -> np.ndarray:
    """
    Ерозія бінарної маски структурним елементом 3x3.
    Піксель залишається активним тільки тоді, коли всі його сусіди активні.
    """
    padded = np.pad(mask, pad_width=1, mode="constant", constant_values=False)

    neighbors = [
        padded[0:-2, 0:-2], padded[0:-2, 1:-1], padded[0:-2, 2:],
        padded[1:-1, 0:-2], padded[1:-1, 1:-1], padded[1:-1, 2:],
        padded[2:, 0:-2], padded[2:, 1:-1], padded[2:, 2:],
    ]

    return np.logical_and.reduce(neighbors)


def dilate(mask: np.ndarray) -> np.ndarray:
    """
    Дилатація бінарної маски структурним елементом 3x3.
    Піксель стає активним, якщо хоча б один сусід активний.
    """
    padded = np.pad(mask, pad_width=1, mode="constant", constant_values=False)

    neighbors = [
        padded[0:-2, 0:-2], padded[0:-2, 1:-1], padded[0:-2, 2:],
        padded[1:-1, 0:-2], padded[1:-1, 1:-1], padded[1:-1, 2:],
        padded[2:, 0:-2], padded[2:, 1:-1], padded[2:, 2:],
    ]

    return np.logical_or.reduce(neighbors)


def denoise(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    """
    Знешумлення методом ерозії-дилатації.
    Спочатку ерозія прибирає дрібні шумові включення,
    потім дилатація частково відновлює основну форму.
    """
    result = mask.copy()

    for _ in range(iterations):
        result = erode(result)

    for _ in range(iterations):
        result = dilate(result)

    return result


def active_ratio(mask: np.ndarray) -> float:
    return float(np.count_nonzero(mask)) / mask.size


def find_threshold_for_half_volume(image: np.ndarray, variant: int, iterations: int = 1) -> tuple[int, np.ndarray]:
    """
    Програмний підбір threshold.
    Мета — отримати після сегментації та знешумлення приблизно 50% активних вокселів.
    """
    target = 0.5
    low = 0
    high = MAX_VALUE

    best_threshold = 0
    best_mask = None
    best_error = float("inf")

    while low <= high:
        mid = (low + high) // 2

        segmented = segment(image, mid, variant)
        filtered = denoise(segmented, iterations=iterations)

        ratio = active_ratio(filtered)
        error = abs(ratio - target)

        if error < best_error:
            best_error = error
            best_threshold = mid
            best_mask = filtered

        # Для парного варіанта умова image <= threshold:
        # збільшення threshold збільшує кількість активних пікселів.
        if variant % 2 == 0:
            if ratio < target:
                low = mid + 1
            else:
                high = mid - 1
        else:
            if ratio < target:
                high = mid - 1
            else:
                low = mid + 1

    return best_threshold, best_mask


def save_pgm(filename: Path, image: np.ndarray, max_value: int) -> None:
    """
    Збереження одноканального зображення у форматі PGM P2.
    """
    h, w = image.shape

    with open(filename, "w", encoding="ascii") as file:
        file.write("P2\n")
        file.write(f"{w} {h}\n")
        file.write(f"{max_value}\n")

        for y in range(h):
            row = " ".join(str(int(v)) for v in image[y])
            file.write(row + "\n")


def mask_to_uint8(mask: np.ndarray) -> np.ndarray:
    """
    Перетворення бінарної маски у 8-бітне зображення:
    активні пікселі — чорні, фон — білий.
    """
    return np.where(mask, 0, 255).astype(np.uint8)


def save_preview_png(filename: Path, image: np.ndarray) -> None:
    """
    Збереження PNG-превʼю для перегляду в PyCharm або звичайному переглядачі.
    """
    from PIL import Image

    image = image.astype(np.uint8)
    Image.fromarray(image, mode="L").save(filename)


def save_comparison_png(
        filename: Path,
        input_image: np.ndarray,
        raw_mask: np.ndarray,
        denoised_mask: np.ndarray,
        threshold: int,
        raw_ratio: float,
        denoised_ratio: float
) -> None:
    from PIL import Image, ImageDraw

    input_8bit = ((input_image.astype(np.float64) / MAX_VALUE) * 255).astype(np.uint8)

    img1 = Image.fromarray(input_8bit, mode="L").resize((300, 250))
    img2 = Image.fromarray(mask_to_uint8(raw_mask), mode="L").resize((300, 250))
    img3 = Image.fromarray(mask_to_uint8(denoised_mask), mode="L").resize((300, 250))

    canvas = Image.new("RGB", (900, 330), "white")
    canvas.paste(img1.convert("RGB"), (0, 60))
    canvas.paste(img2.convert("RGB"), (300, 60))
    canvas.paste(img3.convert("RGB"), (600, 60))

    draw = ImageDraw.Draw(canvas)

    draw.text((80, 10), "Input 16-bit image", fill=(0, 0, 0))
    draw.text((360, 10), f"Raw segmentation", fill=(0, 0, 0))
    draw.text((650, 10), f"Denoised result", fill=(0, 0, 0))

    draw.text((325, 30), f"threshold = {threshold}", fill=(0, 0, 0))
    draw.text((325, 45), f"active = {raw_ratio * 100:.2f}%", fill=(0, 0, 0))

    draw.text((625, 30), f"threshold = {threshold}", fill=(0, 0, 0))
    draw.text((625, 45), f"active = {denoised_ratio * 100:.2f}%", fill=(0, 0, 0))

    canvas.save(filename)


def run_scaling_experiment(base_image: np.ndarray, variant: int) -> None:
    """
    Невеликий експеримент зі швидкодією для різних масштабів.
    """
    print("\nЕксперимент зі швидкодією:")
    print(f"{'Scale':>6} | {'Size':>10} | {'Threshold':>9} | {'Active %':>9} | {'Time, ms':>10}")
    print("-" * 60)

    for factor in [1, 2, 4, 8]:
        image = upscale_nearest(base_image, factor) if factor > 1 else base_image

        start = time.perf_counter()
        threshold, result = find_threshold_for_half_volume(image, variant, iterations=1)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(
            f"{factor:>6} | "
            f"{image.shape[1]}x{image.shape[0]:<5} | "
            f"{threshold:>9} | "
            f"{active_ratio(result) * 100:>8.2f}% | "
            f"{elapsed_ms:>10.3f}"
        )

def save_summary_txt(
        filename: Path,
        threshold: int,
        total_voxels: int,
        raw_active: int,
        denoised_active: int,
        raw_ratio: float,
        denoised_ratio: float,
        elapsed_ms: float
) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Лабораторна робота №4\n")
        f.write("Тема: Знешумлювання воксельної моделі\n\n")
        f.write(f"Варіант: {VARIANT}\n")
        f.write(f"Глибина каналу: {BIT_DEPTH} біт\n")
        f.write(f"Знайдений threshold: {threshold}\n")
        f.write(f"Кількість усіх вокселів: {total_voxels}\n")
        f.write(f"Активних після сегментації: {raw_active} ({raw_ratio * 100:.2f}%)\n")
        f.write(f"Активних після знешумлення: {denoised_active} ({denoised_ratio * 100:.2f}%)\n")
        f.write(f"Час підбору threshold: {elapsed_ms:.3f} мс\n")
        f.write(f"Відхилення від 50% після знешумлення: {abs(denoised_ratio - 0.5) * 100:.2f}%\n")


def main() -> None:
    print("Лабораторна робота №4")
    print("Тема: Знешумлювання воксельної моделі")
    print(f"Варіант: {VARIANT}")
    print(f"Глибина каналу: {BIT_DEPTH} біт")

    base_8bit = generate_orca_raster_8bit()
    base_8bit = upscale_nearest(base_8bit, factor=8)

    image_16bit = make_16bit_noisy_image(base_8bit)

    start = time.perf_counter()

    threshold, segmented_denoised = find_threshold_for_half_volume(
        image_16bit,
        variant=VARIANT,
        iterations=1,
    )

    segmented_raw = segment(image_16bit, threshold, VARIANT)

    elapsed_ms = (time.perf_counter() - start) * 1000

    raw_ratio = active_ratio(segmented_raw)
    denoised_ratio = active_ratio(segmented_denoised)
    total_voxels = image_16bit.size
    raw_active = int(np.count_nonzero(segmented_raw))
    denoised_active = int(np.count_nonzero(segmented_denoised))

    print("\nОсновний результат:")
    print(f"Розмір зображення: {image_16bit.shape[1]} x {image_16bit.shape[0]}")
    print(f"Кількість усіх вокселів: {total_voxels}")
    print(f"Знайдений threshold: {threshold}")
    print(f"Активних після сегментації: {raw_active} ({raw_ratio * 100:.2f}%)")
    print(f"Активних після знешумлення: {denoised_active} ({denoised_ratio * 100:.2f}%)")
    print(f"Відхилення від 50% після знешумлення: {abs(denoised_ratio - 0.5) * 100:.2f}%")
    print(f"Час підбору threshold: {elapsed_ms:.3f} мс")

    save_pgm(OUTPUT_DIR / "input_16bit.pgm", image_16bit, MAX_VALUE)
    save_pgm(OUTPUT_DIR / "segmented_raw.pgm", mask_to_uint8(segmented_raw), 255)
    save_pgm(OUTPUT_DIR / "segmented_denoised.pgm", mask_to_uint8(segmented_denoised), 255)

    save_preview_png(OUTPUT_DIR / "segmented_raw.png", mask_to_uint8(segmented_raw))
    save_preview_png(OUTPUT_DIR / "segmented_denoised.png", mask_to_uint8(segmented_denoised))

    save_comparison_png(
        OUTPUT_DIR / "comparison.png",
        image_16bit,
        segmented_raw,
        segmented_denoised,
        threshold,
        raw_ratio,
        denoised_ratio
    )

    save_summary_txt(
        OUTPUT_DIR / "summary.txt",
        threshold,
        total_voxels,
        raw_active,
        denoised_active,
        raw_ratio,
        denoised_ratio,
        elapsed_ms
    )


    print("\nФайли збережено:")
    print("output/input_16bit.pgm")
    print("output/segmented_raw.pgm")
    print("output/segmented_denoised.pgm")
    print("output/segmented_raw.png")
    print("output/segmented_denoised.png")
    print("output/comparison.png")
    print("output/comparison.png")
    print("output/summary.txt")

    run_scaling_experiment(image_16bit, VARIANT)


if __name__ == "__main__":
    main()