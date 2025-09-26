from PIL import Image
import numpy as np

def ssim(img1: Image.Image, img2: Image.Image) -> float:
    img1_gray = np.array(img1.convert('L'))
    img2_gray = np.array(img2.convert('L'))
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    mu1, mu2 = np.mean(img1_gray), np.mean(img2_gray)
    sigma1_sq, sigma2_sq = np.var(img1_gray), np.var(img2_gray)
    sigma12 = np.cov(img1_gray.flatten(), img2_gray.flatten())[0][1]
    numerator = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
    denominator = (mu1 ** 2 + mu2 ** 2 + C1) * (sigma1_sq + sigma2_sq + C2)
    return numerator / denominator if denominator != 0 else 0.0