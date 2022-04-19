from weather import AviationWeather as AW
import datetime
from PIL import Image, ImageDraw, ImageFont
import dateutil.parser
import re
from functools import cmp_to_key

FONT_FACTOR=216

def Text(draw, *args, **kwargs):
    bbox = draw.textbbox(args[0], args[1])
    draw.text(*args, **kwargs)
    return bbox

def CenterText(draw, center, text):
    bbox = draw.textbbox((0,0), text)
    cx, cy = bbox[2] / 2, bbox[3] / 2
    x, y = center[0] - cx, center[1] - cy
    draw.text((x, y), text, align="center")
    
def BuildWindText(wx):
    wind_speed = int("0" + wx["wind_speed_kt"])
    wind_gust = int("0" + wx["wind_gust_kt"])

    if wind_speed == 0 and wind_gust == 0:
        return "Wind\nCalm"

    raw = wx["raw_text"]
    if re.findall(r"VRB\d\dKT", raw):
        wind_direction = "Variable"
    else:
        wind_direction = "Wind %03d°" % int(wx["wind_dir_degrees"])
    
    vrb = re.findall(r"\s(\d\d\d)V(\d\d\d)\s", raw)
    if vrb:
        wind_direction += "\nv %s°-%s°" % vrb[0]
            
    result = wind_direction + "\n" + f"{wind_speed}kt"
    if wind_gust:
        result += f"\ngust {wind_gust}kt"

    return result

def cmp_cloud(a, b):
    la = a[2] != ""
    lb = b[2] != ""
    if la != lb:
        return lb - la
    ca = a[0] in ["BKN", "OVC"]
    cb = b[0] in ["BKN", "OVC"]
    if ca != cb:
        return cb - ca
    return int(a[1]) - int(b[1])

def BuildCloudText(wx):
    raw = wx["raw_text"]
    if re.findall(r"\s(SKC|CLR)\s", raw):
        return "Sky\nClear"
    
    m = re.findall(r"\sVV(\d+)", raw)
    if m:
        return "Vertical\nVisibility\n%s'" % m[0]
    
    m = re.findall(r"\s(FEW|SCT|BKN|OVC)(\d+)(TCU|CB)?", raw)
    m.sort(key=cmp_to_key(cmp_cloud))
    if m:
        return "\n".join(map(lambda x:"".join(x), m[:4]))
    return "Sky\nClear"

def BuildRawText(wx):
    raw = wx["raw_text"]
    segs = raw.strip("$").strip().split(" ")
    result = ""
    last_len = 0
    for s in segs:
        if last_len + len(s) < 34 and s != "RMK":
            last_len += 1 + len(s)
            result += " "
        else:
            last_len = len(s)
            result += "\n"
        result += s
    return result.strip()


def BuildMetarCard(airport, side_inch=2.25, dpi=96):
    side = int(side_inch * dpi)
    cw, ch = side // 36, side // 16.75
    ff = side / FONT_FACTOR

    img = Image.new("1", (side, int(side + ch * 3)), 255)
    d = ImageDraw.Draw(img)
    
    wx = AW.METAR(airport)[airport]

    obs_time = dateutil.parser.parse(wx["observation_time"])
    obs_time = obs_time.astimezone(datetime.timezone(datetime.timedelta(hours=-7)))
    obs_time = obs_time.strftime(" Issued: %a %m/%d/%Y %I:%M %p")
    
    fa = []
    fm = []
    for i in range(10):
        fa.append(ImageFont.truetype("Arial.ttf", size=int((i+2)*5*ff)))
        fm.append(ImageFont.truetype("PTMono.ttc", size=int((i+2)*5*ff)))
    
    d.font = fm[0]
    Text(d, (0, 0), obs_time)
    
    d.font = fa[6]
    _, y0, x, y1 = Text(d, (cw, ch//2), airport)
    d.font = fa[3]
    fc = AW.FlightCategory(wx)
    x0, _, x1, _ = Text(d, (x, ch), " " + fc + " ")
    
    if "IFR" in fc:
        c0, c1 = "black", "white"
    else:
        c0, c1 = "white", "black"
    
    d.rectangle((x0+cw, y0-ch//8, x1 + cw, y1-ch//4), fill=c0, outline=c1)
    r = Text(d, (x, ch), "  " + fc + " ", fill=c1)
    
    info_y = ch * 4
    d.line((cw, info_y + 6 * ch, side-cw, info_y + 6*ch), fill="black", width=2)
    d.line((side // 2, info_y, side // 2, info_y + 10*ch), fill="black", width=2)
    
    d.font = fm[1]
    
    center = (side / 4, info_y + 3 * ch)
    CenterText(d, center, BuildWindText(wx))

    center = (side * 3 / 4, info_y + 3 * ch)
    CenterText(d, center, BuildCloudText(wx))
    
    center = (side / 4, info_y + 8 * ch)
    CenterText(d, center, f'Visibility\n{float(wx["visibility_statute_mi"])}mi')
    
    center = (side * 3 / 4, info_y + 8 * ch)
    CenterText(d, center, f'Altimeter\n{round(float(wx["altim_in_hg"]), 2)}\"')

    d.font = fm[0]
    x0,y0,x1,y1 = Text(d, (cw, info_y + 10.5 * ch), BuildRawText(wx))
    d.rectangle((cw-3,y0-3,side-cw+3, img.size[1] - 2 ))
    return img
