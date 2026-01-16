from PIL import Image, ImageDraw

img = Image.new("RGB", (640, 640), (235, 235, 235))
d = ImageDraw.Draw(img)
d.rectangle([80, 80, 560, 560], outline=(180, 180, 180), width=6)
d.text((120, 300), "Triangulum", fill=(120, 120, 120))
img.save(r"web\assets\placeholder.webp", "WEBP", quality=85, method=6)

print("placeholder.webp=OK")
