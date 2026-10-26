# Asset origins

The site uses supplied autorelabel assets and genuine terminal screenshots. It contains no stock photography or replacement product illustrations.

| Files | Origin and treatment |
| --- | --- |
| `public/brand/*.svg` | Supplied autorelabel brand kit. Marks retain their original colours and geometry. The selected header mark is the mono wordmark. |
| `favicon-32.png`, `apple-touch-icon.png`, `icon-512.png` | PNG rasterizations of the supplied `icon-slashdot.svg` at the named dimensions. |
| `icon-maskable-512.png` | The same supplied icon, with safe-area padding on its existing night ground. |
| `public/social-preview.png` | Repository `docs/social-preview.png`, supplied social card. |
| Home, exam and results images | Repository `docs/media/home.png`, `exam.png`, and `results.png`. Astro prepares local WebP sizes for the page and guide layouts. The original product screens remain the visual source. |
| `public/media/demo-720.mp4` and `.webm` | The supplied 1080p autorelabel demo MP4, scaled to 1280×720. The exact conversion commands are in `README.md`. |
| `public/media/demo-poster.avif` | Frame at twelve seconds in the supplied demo, scaled to 1280×720 and saved as AVIF. |
| `public/fonts/*.woff2` | Self-hosted Fontsource files. The headline Latin faces preserve the selected settings: weight 650, optical size 80, softness 25 and WONK 1. Other 650-weight Latin faces retain optical-size and softness axes. The 400-weight italic note face fixes the default softness at 0 and retains optical sizing. Full supplied variable faces cover the remaining weights and glyphs. The optional preparation script records these derivations. Atkinson Hyperlegible Next and JetBrains Mono retain the supplied subsets and weights. |
| Font licence text files | Original licences distributed with the font assets, copied without changes. |

SVG geometry, CSS annotation paths, and the lab diagram are code-native elements. The AVIF poster and video origins are recorded here.
