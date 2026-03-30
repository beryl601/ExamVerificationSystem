import qrcode
import os
def generate_qr(reg_number, save_folder="static/qrcodes"):
    """
    Create a QR code image for a student registration number.
    Parameters:
        reg_number  (str): The student reg number, e.g. SCT221-0001/2022
        save_folder (str): Folder where the image is saved
    Returns:
        str: The file path of the saved QR code image
    """
    os.makedirs(save_folder, exist_ok=True)  # Create folder if it does not exist
    qr   = qrcode.make(reg_number)           # Create the QR code image
    path = os.path.join(save_folder, f"{reg_number}.png")
    qr.save(path)                            # Save as PNG file
    return path  # Return the path so we can store it in the database