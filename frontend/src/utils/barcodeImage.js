export function binarizeBarcodeImage(image) {
    const pixels = image.data;
    for (let i = 0; i < pixels.length; i += 4) {
        // shortcut: 160 is calibrated on retained camera frames; expand the cohort before retuning.
        const value = ((77 * pixels[i] + 150 * pixels[i + 1] + 29 * pixels[i + 2]) >> 8) < 160 ? 0 : 255;
        pixels[i] = pixels[i + 1] = pixels[i + 2] = value;
        pixels[i + 3] = 255;
    }
    return image;
}
