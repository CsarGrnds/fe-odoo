import qrcode


def _check_image_size(self, size):
    """ Check and fix the size of the image to 32 bits """
    if size % 32 == 0:
        return (0, 0)
    else:
        image_border = 32 - (size % 32)
        if (image_border % 2) == 0:
            return (image_border / 2, image_border / 2)
        else:
            return (image_border / 2, (image_border / 2) + 1)

def _convert_image(im):
    """ Parse image and prepare it to a printable format """
    pixels = []
    pix_line = ""
    im_left = ""
    im_right = ""
    switch = 0
    img_size = [0, 0]

    if im.size[0] > 512:
        print("WARNING: Image is wider than 512 and could be truncated at print time ")
    if im.size[1] > 255:
        print "Error"

    im_border = _check_image_size(im.size[0])
    for i in range(im_border[0]):
        im_left += "0"
    for i in range(im_border[1]):
        im_right += "0"

    for y in range(im.size[1]):
        img_size[1] += 1
        pix_line += im_left
        img_size[0] += im_border[0]
        for x in range(im.size[0]):
            img_size[0] += 1
            RGB = im.getpixel((x, y))
            im_color = (RGB[0] + RGB[1] + RGB[2])
            im_pattern = "1X0"
            pattern_len = len(im_pattern)
            switch = (switch - 1) * (-1)
            for x in range(pattern_len):
                if im_color <= (255 * 3 / pattern_len * (x + 1)):
                    if im_pattern[x] == "X":
                        pix_line += "%d" % switch
                    else:
                        pix_line += im_pattern[x]
                    break
                elif im_color > (255 * 3 / pattern_len * pattern_len) and im_color <= (255 * 3):
                    pix_line += im_pattern[-1]
                    break
        pix_line += im_right
        img_size[0] += im_border[1]

    return (pix_line, img_size)

def qr(text):
    """ Print QR Code for the provided string """
    qr_code = qrcode.QRCode(version=4, box_size=4, border=1)
    qr_code.add_data(text)
    qr_code.make(fit=True)
    qr_img = qr_code.make_image()
    im = qr_img._img.convert("RGB")
    # Convert the RGB image in printable image
    return _convert_image(im)

print qr('50629041800030412028600100001010000000030199999999')