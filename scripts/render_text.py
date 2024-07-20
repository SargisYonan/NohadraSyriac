import sys
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

def render_text_to_image(font_path, text, output_path):
    width, height = 5000, 500

    # Create a new image with a white background
    image = Image.new('RGB', (width, height), color='white')

    # Prepare the text for rendering
    reshaped_text = arabic_reshaper.reshape(text.strip())
    
    # Load the font
    font_size = 400
    font = ImageFont.truetype(font_path, font_size)

    # Calculate text width and height for centering
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), reshaped_text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_x = (width - text_width) // 2
    text_y = ((height - text_height) // 2) - text_height/2

    # Draw the text on the image
    text_color = (0, 0, 0)  # Black color
    draw.text((text_x, text_y), reshaped_text, fill=text_color, font=font)

    # Save the image
    image.save(output_path)
    print(f"Image saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python render_text.py <font_path> <text> <output_path>")
        sys.exit(1)
    
    font_path = sys.argv[1]
    text = sys.argv[2]
    output_path = sys.argv[3]

    render_text_to_image(font_path, text, output_path)
