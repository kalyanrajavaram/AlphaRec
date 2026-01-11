# Extension Icons Required

For the Chrome extension to work properly, you need to create three icon files in this directory:

## Required Files

1. **icon16.png** - 16x16 pixels
2. **icon48.png** - 48x48 pixels
3. **icon128.png** - 128x128 pixels

## Quick Creation Methods

### Option 1: Online Generator (Easiest - 2 minutes)

1. Go to https://favicon.io/favicon-generator/
2. Enter text: "A" (or any letter/icon you want)
3. Choose colors (recommended: #667eea background, white text)
4. Click "Generate" and download the zip file
5. Extract and rename files:
   - `favicon-16x16.png` → `icon16.png`
   - `favicon-32x32.png` → resize to 48x48 → `icon48.png`
   - `android-chrome-512x512.png` → resize to 128x128 → `icon128.png`

### Option 2: Use Preview (macOS Built-in)

1. Create a 128x128 image:
   - Open Preview
   - File → New from Clipboard (or create blank)
   - Tools → Adjust Size → 128x128 pixels
   - Fill with a color (#667eea recommended)
   - Save as `icon128.png`

2. Create smaller versions:
   - Open `icon128.png` in Preview
   - Tools → Adjust Size → 48x48 pixels
   - Save as `icon48.png`
   - Repeat for 16x16 → `icon16.png`

### Option 3: Command Line (ImageMagick)

If you have ImageMagick installed:

```bash
# Create a purple square icon
convert -size 128x128 xc:#667eea icon128.png
convert icon128.png -resize 48x48 icon48.png
convert icon128.png -resize 16x16 icon16.png
```

### Option 4: Download from Icon Libraries

Free icon resources:
- https://www.flaticon.com/ (search "activity" or "tracker")
- https://icons8.com/ (download PNG at required sizes)
- https://www.iconfinder.com/ (free icons available)

## Verification

After creating the icons, verify they exist:

```bash
ls -lh chrome-extension/icons/
```

You should see:
```
icon16.png  (16x16, ~1-2 KB)
icon48.png  (48x48, ~2-4 KB)
icon128.png (128x128, ~4-8 KB)
```

## Color Recommendations

To match the extension's theme:
- **Background**: #667eea (purple-blue)
- **Foreground**: #ffffff (white)
- **Accent**: #764ba2 (darker purple)

## What If I Don't Create Icons?

Chrome will:
- Show a warning in the extension page
- Display a default placeholder icon
- **The extension will still work functionally**

However, it's recommended to create proper icons for a professional appearance.

## Example Design Ideas

Simple but effective:
- Letter "A" on colored background
- Activity graph icon
- Eye icon (for tracking/watching)
- Clock icon (for time tracking)
- Bar chart icon

Keep it simple - a single letter or basic shape works perfectly!
