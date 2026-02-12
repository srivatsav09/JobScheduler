"""Generate a sample image for thumbnail job demos."""
from PIL import Image, ImageDraw

img = Image.new("RGB", (800, 600), color=(41, 128, 185))
draw = ImageDraw.Draw(img)

# Draw a simple grid pattern so the thumbnail is visually interesting
for x in range(0, 800, 40):
    draw.line([(x, 0), (x, 600)], fill=(52, 152, 219), width=1)
for y in range(0, 600, 40):
    draw.line([(0, y), (800, y)], fill=(52, 152, 219), width=1)

# Draw a centered rectangle
draw.rectangle([200, 150, 600, 450], fill=(231, 76, 60), outline=(192, 57, 43), width=3)

img.save("sample_data/sample.jpg", "JPEG", quality=85)
print("Created sample_data/sample.jpg (800x600)")
