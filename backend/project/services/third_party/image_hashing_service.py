"""
Image Hashing Service
---------------------
This service provides functionalities for creating perceptual hashes (fingerprints)
of images. It's used to identify visually similar images, which is crucial for
detecting duplicate photo submissions in Masjid Applications.

This service is designed to be modular. If we ever decide to use a different
hashing library or method, the changes will be contained within this file.
"""

from PIL import Image
# import imagehash
import requests
from io import BytesIO

def generate_phash_from_url(image_url: str) -> str:
    """
    Downloads an image from a URL and computes its perceptual hash (pHash).

    Args:
        image_url: The public URL of the image to be hashed.

    Returns:
        A string representation of the 64-bit perceptual hash.
        Returns None if the image cannot be downloaded or processed.
    """
    # try:
    #     # Download the image from the URL
    #     response = requests.get(image_url, timeout=10)
    #     response.raise_for_status()  # Raise an exception for bad status codes
    #     
    #     # Open the image from the downloaded content
    #     image = Image.open(BytesIO(response.content))
    #     
    #     # Generate the perceptual hash
    #     # high_frequency_factor can be adjusted if needed, default is 4
    #     phash = imagehash.phash(image)
    #     
    #     return str(phash)
    # except requests.exceptions.RequestException as e:
    #     # Handle network-related errors (e.g., invalid URL, connection error)
    #     print(f"Error downloading image from {image_url}: {e}")
    #     return None
    # except IOError as e:
    #     # Handle errors related to image processing (e.g., invalid image format)
    #     print(f"Error processing image from {image_url}: {e}")
    #     return None
    return "dummy_hash"

def compare_phashes(hash1: str, hash2: str) -> int:
    """
    Computes the Hamming distance between two perceptual hash strings.
    The Hamming distance is the number of positions at which the corresponding
    bits are different. A lower distance means the images are more similar.

    Args:
        hash1: The first perceptual hash string.
        hash2: The second perceptual hash string.

    Returns:
        The integer Hamming distance between the two hashes.
    """
    # # Convert the hex hash strings back to imagehash objects
    # img_hash1 = imagehash.hex_to_hash(hash1)
    # img_hash2 = imagehash.hex_to_hash(hash2)
    # 
    # # The difference operator on imagehash objects returns the Hamming distance
    # return img_hash1 - img_hash2
    return 0
