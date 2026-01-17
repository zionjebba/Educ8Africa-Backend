"""
QR Code Generator Service
A service class for generating customized QR codes with company logo watermark.
"""

import qrcode
from PIL import Image, ImageEnhance
import os
import base64
from io import BytesIO
from typing import Optional, Dict
import traceback


class QRCodeGeneratorService:
    """Service for generating QR codes with company logo watermark."""
    
    def __init__(
        self,
        logo_path: str = "app/static/images/yellow-logo.png",
        default_qr_size: int = 10,
        default_border: int = 2,
        default_fill_color: str = "#0A2463",
        default_back_color: str = "white",
        default_logo_opacity: float = 0.75,
        default_logo_size_ratio: float = 0.3
    ):
        """
        Initialize the QR Code Generator Service.
        
        Args:
            logo_path: Default path to company logo
            default_qr_size: Default QR code box size
            default_border: Default border size
            default_fill_color: Default QR code color
            default_back_color: Default background color
            default_logo_opacity: Default logo transparency
            default_logo_size_ratio: Default logo size ratio
        """
        self.logo_path = logo_path
        self.default_qr_size = default_qr_size
        self.default_border = default_border
        self.default_fill_color = default_fill_color
        self.default_back_color = default_back_color
        self.default_logo_opacity = default_logo_opacity
        self.default_logo_size_ratio = default_logo_size_ratio
    
    def generate_qr_code_with_logo(
        self,
        data: str,
        logo_path: Optional[str] = None,
        qr_size: Optional[int] = None,
        border: Optional[int] = None,
        fill_color: Optional[str] = None,
        back_color: Optional[str] = None,
        logo_opacity: Optional[float] = None,
        logo_size_ratio: Optional[float] = None
    ) -> Image.Image:
        """
        Generate a QR code with logo as transparent background watermark.
        
        Args:
            data: The URL or data to encode in the QR code
            logo_path: Path to logo (uses default if None)
            qr_size: Size of each QR code box
            border: Border size in boxes
            fill_color: QR code color
            back_color: Background color
            logo_opacity: Transparency of the logo (0.0-1.0)
            logo_size_ratio: Ratio of logo size to QR code size (0.0-1.0)
        
        Returns:
            PIL Image object of the QR code
        """
        # Use defaults if not provided
        logo_path = logo_path or self.logo_path
        qr_size = qr_size or self.default_qr_size
        border = border or self.default_border
        fill_color = fill_color or self.default_fill_color
        back_color = back_color or self.default_back_color
        logo_opacity = logo_opacity if logo_opacity is not None else self.default_logo_opacity
        logo_size_ratio = logo_size_ratio if logo_size_ratio is not None else self.default_logo_size_ratio
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=qr_size,
            border=border,
        )
        
        # Add data to QR code
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color=fill_color, back_color=back_color).convert('RGBA')
        
        # Check if logo exists
        if not os.path.exists(logo_path):
            print(f"Warning: Logo not found at {logo_path}. Generating QR code without logo.")
            return qr_img.convert('RGB')
        
        try:
            # Open and process logo
            logo = Image.open(logo_path).convert('RGBA')
            
            # Get QR code dimensions
            qr_width, qr_height = qr_img.size
            
            # Calculate logo size
            logo_target_width = int(qr_width * logo_size_ratio)
            logo_target_height = int(qr_height * logo_size_ratio)
            
            # Get logo aspect ratio
            logo_aspect = logo.size[0] / logo.size[1]
            
            # Resize logo to fit the target dimensions while maintaining aspect ratio
            if logo_aspect > 1:  # Wider logo
                new_width = logo_target_width
                new_height = int(new_width / logo_aspect)
            else:  # Taller or square logo
                new_height = logo_target_height
                new_width = int(new_height * logo_aspect)
            
            # Make sure logo is not smaller than target
            if new_width < logo_target_width or new_height < logo_target_height:
                scale = max(logo_target_width / new_width, logo_target_height / new_height)
                new_width = int(new_width * scale)
                new_height = int(new_height * scale)
            
            logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Adjust logo opacity
            if logo_opacity < 1.0:
                logo_with_alpha = logo.copy()
                
                if logo_with_alpha.mode == 'RGBA':
                    alpha = logo_with_alpha.split()[3]
                else:
                    alpha = Image.new('L', logo_with_alpha.size, 255)
                
                alpha = ImageEnhance.Brightness(alpha).enhance(logo_opacity)
                logo_with_alpha.putalpha(alpha)
                logo = logo_with_alpha
            
            # Create a new image with white background
            final_img = Image.new('RGBA', (qr_width, qr_height), back_color)
            
            # Calculate position to center the logo
            logo_x = (qr_width - logo.size[0]) // 2
            logo_y = (qr_height - logo.size[1]) // 2
            
            # Paste the transparent logo as background
            final_img.paste(logo, (logo_x, logo_y), logo)
            
            # Overlay the QR code on top
            qr_data = qr_img.getdata()
            new_qr_data = []
            
            for item in qr_data:
                # If pixel is white (background), make it transparent
                if item[:3] == (255, 255, 255):
                    new_qr_data.append((255, 255, 255, 0))
                else:
                    # Keep the QR code pattern opaque
                    new_qr_data.append(item)
            
            qr_img.putdata(new_qr_data)
            
            # Composite QR code over logo
            final_img = Image.alpha_composite(final_img, qr_img)
            
            # Convert to RGB for saving
            final_img = final_img.convert('RGB')
            
            return final_img
            
        except Exception as e:
            print(f"Error processing logo: {e}")
            traceback.print_exc()
            return qr_img.convert('RGB')
    
    def generate_qr_code_base64(
        self,
        data: str,
        logo_path: Optional[str] = None,
        qr_size: Optional[int] = None,
        border: Optional[int] = None,
        fill_color: Optional[str] = None,
        back_color: Optional[str] = None,
        logo_opacity: Optional[float] = None,
        logo_size_ratio: Optional[float] = None,
        output_format: str = "PNG"
    ) -> str:
        """
        Generate QR code with logo and return as base64 string.
        
        Args:
            data: The URL or data to encode
            logo_path: Path to logo
            qr_size: Size of each QR code box
            border: Border size
            fill_color: QR code color
            back_color: Background color
            logo_opacity: Logo transparency
            logo_size_ratio: Logo size ratio
            output_format: Image format (PNG, JPEG, etc.)
        
        Returns:
            Base64 encoded string of the QR code image
        """
        qr_img = self.generate_qr_code_with_logo(
            data=data,
            logo_path=logo_path,
            qr_size=qr_size,
            border=border,
            fill_color=fill_color,
            back_color=back_color,
            logo_opacity=logo_opacity,
            logo_size_ratio=logo_size_ratio
        )
        
        # Convert to base64
        buffered = BytesIO()
        qr_img.save(buffered, format=output_format, quality=95)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str
    
    def generate_qr_code_data_uri(
        self,
        data: str,
        **kwargs
    ) -> str:
        """
        Generate QR code and return as data URI for direct use in HTML/emails.
        
        Args:
            data: The URL or data to encode
            **kwargs: Additional arguments passed to generate_qr_code_base64
        
        Returns:
            Data URI string (data:image/png;base64,...)
        """
        output_format = kwargs.pop('output_format', 'PNG')
        base64_str = self.generate_qr_code_base64(
            data=data,
            output_format=output_format,
            **kwargs
        )
        
        mime_type = f"image/{output_format.lower()}"
        return f"data:{mime_type};base64,{base64_str}"
    
    def save_qr_code(
        self,
        data: str,
        output_path: str,
        **kwargs
    ) -> str:
        """
        Generate and save QR code to a file.
        
        Args:
            data: The URL or data to encode
            output_path: Path where to save the QR code
            **kwargs: Additional arguments passed to generate_qr_code_with_logo
        
        Returns:
            Path to the saved file
        """
        qr_img = self.generate_qr_code_with_logo(data=data, **kwargs)
        
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Save the image
        qr_img.save(output_path, quality=95)
        
        return output_path