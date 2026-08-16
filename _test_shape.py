imd1 = 'Cinematic, a medium-wide shot frames a colorful box of waffle cakes sliding smoothly into view from the left side of the frame against a clean, bright white background.'
text = imd1.lower()
shape_kws = [
    (("round", "sphere", "ball", "globe", "circle", "spherical", "orb", "dome"), "round"),
    (("cylinder", "bottle", "can", "tube", "jar", "barrel", "roll", "cylindrical"), "cylinder"),
    (("irregular", "organic", "lump", "blob", "amorphous", "uneven", "jagged"), "irregular"),
    (("thin", "flaky", "layered", "sheet", "slab", "bar", "stick", "rectangular", "flat"), "rect"),
]
for kws, s in shape_kws:
    for k in kws:
        if k in text:
            print(f"Matched shape={s} via keyword='{k}'")
