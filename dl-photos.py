#!/usr/bin/python

import sys
import getopt
from progress.bar import IncrementalBar
import tempfile
import urllib.request
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import json


def get_page(birder_id, tmp_dir, page_num=1):
    fname = f"{tmp_dir}/{birder_id}-{page_num}.html"
    url = f"http://orientalbirdimages.org/photographers.php?action=birdercontrib&Birder_ID={birder_id}&page={page_num}"
    urllib.request.urlretrieve(url, fname)
    return fname


def get_img_page(birder_id, tmp_dir, img_id):
    fname = f"{tmp_dir}/{birder_id}-img-{img_id}.html"
    url = f"http://orientalbirdimages.org/photographers.php?action=birderimages&Bird_Image_ID={img_id}&Birder_ID={birder_id}"
    urllib.request.urlretrieve(url, fname)
    return fname


def num_of_pages_and_images(main_page):
    def is_int(value):
        try:
            int(value)
            return True
        except:
            return False
    num_page = 1
    num_images = 0
    with open(main_page, 'r') as f:
        content = f.read()
        soup = BeautifulSoup(content, features="html.parser")
        tds = soup.find_all('td', 'paging')

        images_td = tds[0]
        num_images = int(images_td.string.replace(
            "No. of Image(s) : ", "").strip())
        print("Number of images", num_images)

        pages_td = tds[1]
        vals = map(lambda x: x.string, filter(
            lambda x: x.name == 'a', pages_td.contents))
        ints = map(int, filter(is_int, vals))
        num_page = max(ints)
        print("Number of pages", num_page)

    return num_page, num_images


def download_images_and_metadata(page, output_dir, tmp_dir, images_bar):
    with open(page, 'r') as fp:
        content = fp.read()
        soup = BeautifulSoup(content, features="html.parser")
        tds = soup.find_all('td', 'detail')
        trs = set(map(lambda x: x.parent, tds))
        for tr in trs:
            ahref = tr.find('a', 'mlink')['href']
            url = f"http://orientalbirdimages.org/{ahref}"
            image_ids = parse_qs(urlparse(url).query)['Bird_Image_ID']
            assert len(image_ids) == 1
            image_id = image_ids[0]
            img_page = get_img_page(birder_id, tmp_dir, image_id)
            # print(img_page)
            with open(img_page, 'r') as fi:
                content = fi.read()
                soup = BeautifulSoup(content, features="html.parser")
                # img
                img = soup.find_all('img')[1]
                img_url = img['src']
                img_fname = f'{output_dir}/{image_id}.jpg'
                urllib.request.urlretrieve(img_url, img_fname)
                # metadata
                try:
                    metadata = {}
                    table = img.parent.parent.parent
                    if table.contents[0].name:
                        # might have a valid tr then td
                        trs = table.find_all('tr')
                        metadata['title'] = list(
                            map(lambda x: x.string.strip(), trs[0].contents[0].contents))
                        img_src_idx = 1
                        rest_idx = 2
                    else:
                        # first three are title
                        metadata['title'] = list(
                            map(lambda x: x.string.strip(), trs[0].contents[0:3]))
                        img_src_idx = 3
                        rest_idx = 4
                    metadata['img_src'] = trs[img_src_idx].contents[0].contents[0]['src']

                    def clean_str(string):
                        s = string.replace(":", '')
                        s = s.strip()
                        return s
                    for tri in range(rest_idx, len(trs)):
                        tr = trs[tri]
                        key = clean_str(tr.contents[0].text)
                        val = clean_str(tr.contents[1].text)
                        metadata[key] = val
                    mdata_fname = f'{output_dir}/{image_id}.json'
                    with open(mdata_fname, 'w', encoding="utf-8") as fm:
                        json.dump(metadata, fm, indent=2)
                except AttributeError:
                    print('\n', "Skipping (attribute): ", image_id)
                except TypeError:
                    print('\n', "Skipping (type): ", image_id)
            images_bar.next()


def dl_photos(birder_id, tmp_dir, output_dir):
    print("Birder ID:", birder_id)
    print("Temporary folder:", tmp_dir)
    print("Output folder:", output_dir)
    # get main photographer page
    main_page = get_page(birder_id, tmp_dir)
    # get number of image pages
    num_pages, num_images = num_of_pages_and_images(main_page)
    # go through all of them
    pages_bar = IncrementalBar('Pages', max=num_pages)
    images_bar = IncrementalBar('Images', max=num_images)
    for page_num in range(1, num_pages+1):
        page = get_page(birder_id, tmp_dir, page_num)
        # download images
        download_images_and_metadata(page, output_dir, tmp_dir, images_bar)
        pages_bar.next()
    images_bar.finish()
    pages_bar.finish()


if __name__ == "__main__":
    args = sys.argv[1:]
    birder_id = None
    output_dir = None
    with tempfile.TemporaryDirectory(prefix="dl-photos") as tmp_dir:
        try:
            opts, args = getopt.getopt(
                args, "hi:o:", ["birder_id=", "output_dir="])
        except getopt.GetoptError:
            print('dl-photos.py -i <birderid>')
            sys.exit(2)
        for opt, arg in opts:
            if opt == '-h':
                print('dl-photos.py -i <birderid>')
                sys.exit()
            elif opt in ("-i", "--birder_id"):
                birder_id = arg
            elif opt in ("-o", "--output_dir"):
                output_dir = arg
        if birder_id and tmp_dir and output_dir:
            dl_photos(birder_id, tmp_dir, output_dir)
        else:
            print("Not enough arguments.")
            sys.exit(2)
