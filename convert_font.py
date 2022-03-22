import cv2
import base64
import argparse

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def space(char_height, space_length=1):
    return [[0] * char_height] * space_length

def trim_char(char):
    if char and not any(char[0]):
        return trim_char(char[1:])
    elif char and not any(char[-1]):
        return trim_char(char[:-1])
    return char

def img_px_to_binary(n):
    return 1 if n < 128 else 0

def binary_list_to_int(bin_list):
    result = 0
    for digits in bin_list:
        result = (result << 1) | digits
    return result

def list_to_bytes(int_list):
    return b"".join([bytes([i]) for i in int_list])

def flatten(l_to_flat):
    if not l_to_flat:
        return l_to_flat
    if isinstance(l_to_flat[0], list):
        return flatten(l_to_flat[0]) + flatten(l_to_flat[1:])
    return l_to_flat[:1] + flatten(l_to_flat[1:])

def byte_to_str(bytes_to_convert):
    return base64.b64encode(bytes_to_convert).decode('utf-8')

def cv2_img_to_horizontal(cv2_img, char_height):
    return cv2.hconcat(list(chunks(cv2_img, char_height)))

def get_cv2_img(img_path, font_is_white=False):
    cv2_img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
    if len(cv2_img.shape) >2:
        try:
            trans_mask = cv2_img[:, :, 3] == 0
            cv2_img[trans_mask] = [0, 0, 0, 0] if font_is_white else [255, 255, 255, 255]
            cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGRA2GRAY)
        except IndexError:
            cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
    if font_is_white:
        cv2_img = cv2.bitwise_not(cv2_img)
    return cv2_img

def cv2_img_to_espruino_font(
        cv2_font_image,
        first_char,
        # char width if chars have no space between each other on the font image
        # or chars with no content (127 to 160)
        # or chars with white column inside (")
        # better set that value if you have it anyway
        char_w=0,
        fixed_w=False, # fixed width to keep the font monospaced
        space_w=0, # set width for the space character, keep 0 to set half the biggest char
        space_between_chars=1, # set the nb of pixel between chars
        add_space_between_chars=False # add space between chars to fixed width font
    ):
    if fixed_w and not add_space_between_chars:
        space_between_chars = 0
    char_h = cv2_font_image.shape[0]
    sp_between_chars = space(char_h, space_between_chars)
    binary_font_image = [[img_px_to_binary(x) for x in l] for l in cv2_font_image]

    # list of columns of pixels with 0 = white, 1 = black
    transposed_binary_font_image = list(map(list, zip(*binary_font_image)))

    chars = []
    if char_w:
        full_chars = [
            transposed_binary_font_image[i:i+char_w]
            for i in range(0, len(transposed_binary_font_image), char_w)
        ]
        for char in full_chars:
            if not fixed_w:
                char = trim_char(char)
            chars.append(char + sp_between_chars)
    else:
        char = []
        for column in transposed_binary_font_image:
            if any(column):
                char.append(column)
            elif char:
                chars.append(char + sp_between_chars)
                char = []

    if first_char == 32:
        if fixed_w and char_w and not space_w :
            space_w = char_w + space_between_chars
        elif not space_w:
            space_w = int(max([len(char) for char in chars])/2)
        space_char = space(char_h, space_w)
        if char_w:
            chars[0] = space_char
        else:
            chars = space_char + chars

    char_widths = [len(char) for char in chars]
    bits = flatten(chars)

    font_int_list = [binary_list_to_int(b) for b in chunks(bits, 8)]
    font_bytes = list_to_bytes(font_int_list)
    font_width_bytes = list_to_bytes(char_widths)
    return (
        f"var font = atob(\"{byte_to_str(font_bytes)}\");\n"
        f"var widths = atob(\"{byte_to_str(font_width_bytes)}\");\n"
        f"g.setFontCustom(font, {first_char}, widths, {char_h});\n"
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed", help="Font with fixed width (monospaced)", action="store_true")
    parser.add_argument("--white", help="Font with white characters on black background", action="store_true")
    parser.add_argument("--space_width", help="Width of the space character in px", type=int, required=False)
    parser.add_argument("--char_space_width", help="Width of the space between characters in px", type=int, required=False)
    parser.add_argument("filepath", help="Path to image file of the font")
    parser.add_argument("first_char", help="Decimal code of the first character in ISO Latin-1", type=int)
    parser.add_argument("char_height", help="Height of the characters of the font", type=int)
    parser.add_argument("char_width",  help="width of the block containing each character", type=int)

    args = parser.parse_args()
    cv2_img = get_cv2_img(args.filepath, args.white)
    char_height = args.char_height
    if cv2_img.shape[0] > char_height:
        cv2_img = cv2_img_to_horizontal(cv2_img, char_height)

    space_width = args.space_width
    char_space_width = args.char_space_width
    espruino_font = cv2_img_to_espruino_font(
        cv2_font_image=cv2_img,
        first_char=args.first_char,
        char_w=args.char_width,
        fixed_w=args.fixed,
        space_w=space_width if space_width else 0,
        space_between_chars=char_space_width if char_space_width else 1,
        add_space_between_chars=args.fixed and char_space_width
    )
    print(espruino_font)
