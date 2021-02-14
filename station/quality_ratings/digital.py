

def rate(img):
    """Calculate ratio between completly black pixels to all pixels"""
    noise_mask = img == 0
    if img.ndim == 3:
        noise_factors = noise_mask.sum(axis=2) == 3
    else: # 2D or 1D
        noise_factors = noise_mask
    return 1 - noise_factors.mean()
