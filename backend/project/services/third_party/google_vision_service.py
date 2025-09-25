"""
Google Vision API Service
-------------------------
This service acts as a modular interface for interacting with the Google Cloud
Vision API. It abstracts the details of the API calls, making it easy to use
its features throughout the application.

Currently, it's used for Optical Character Recognition (OCR) on documents
submitted with Masjid Applications.

If we ever need to switch to a different OCR provider, the changes required
will be isolated to this file, by creating a new service that adheres to the
same interface.
"""

from google.cloud import vision
import requests

def detect_text_in_document_from_url(image_url: str) -> str:
    """
    Performs OCR on an image from a given URL using the Google Vision API.

    Args:
        image_url: The public URL of the document image.

    Returns:
        A string containing all the text detected in the document.
        Returns None if there is an error.
    """
    try:
        # Initialize the Vision API client
        # The client automatically uses the credentials from the 
        # GOOGLE_APPLICATION_CREDENTIALS environment variable.
        client = vision.ImageAnnotatorClient()

        # Download the image content from the URL
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        content = response.content

        # Prepare the image for the Vision API
        image = vision.Image(content=content)

        # Perform text detection (OCR)
        response = client.text_detection(image=image)
        texts = response.text_annotations

        if response.error.message:
            raise Exception(
                f'{response.error.message}\nFor more info on error messages, check: \n'
                'https://cloud.google.com/apis/design/errors'
            )

        if texts:
            # The first text annotation contains the full detected text block.
            return texts[0].description
        else:
            return ""
            
    except Exception as e:
        print(f"An error occurred while calling Google Vision API: {e}")
        return None
