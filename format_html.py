import os
import re
from bs4 import BeautifulSoup

DETAILS_DIR = 'details'
TEMPLATE_FILE = os.path.join(DETAILS_DIR, 'Entre08.html')
FILES_TO_IGNORE = ['Entre03.html', 'Entre08.html']

def get_template_style():
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')
        return soup.find('style')

def format_html_file(file_path, style_template):
    print(f"  - Reading and parsing {os.path.basename(file_path)}")
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')

    # --- Restructure Head ---
    head = soup.head
    if not head:
        head = soup.new_tag('head')
        soup.html.insert(0, head)

    title_tag = soup.new_tag('title')
    french_name, english_name = '', ''

    if soup.body:
        p_tags = soup.body.find_all('p', {'align': 'center'}, limit=3)
        if len(p_tags) >= 1:
            french_name_tag = p_tags[0]
            english_name_tag = None
            
            if len(p_tags) > 1:
                for i in range(1, len(p_tags)):
                    if p_tags[i] and 'name:' in p_tags[i].get_text():
                        english_name_tag = p_tags[i]
                        break
                if not english_name_tag: 
                    english_name_tag = p_tags[1]

            if french_name_tag:
                french_name = french_name_tag.get_text(strip=True).replace('\n', ' ')
                french_name_tag.extract()

            if english_name_tag:
                english_name_text = english_name_tag.get_text(strip=True).replace('\n', ' ')
                if 'name:' in english_name_text:
                    english_name = english_name_text.split('name:')[1].strip()
                else:
                    english_name = english_name_text
                english_name_tag.extract()

    title_tag.string = f"{french_name} / {english_name}" if french_name and english_name else os.path.basename(file_path)
    
    print(f"    - Title set to: {title_tag.string}")

    head.clear()
    head.append(soup.new_tag('meta', attrs={'charset': 'UTF-8'}))
    head.append(soup.new_tag('meta', attrs={'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}))
    head.append(title_tag)
    head.append(soup.new_tag('link', attrs={'rel': 'icon', 'type': 'image/png', 'sizes': '32x32', 'href': '../img/favicon32.png'}))
    head.append(soup.new_tag('link', attrs={'rel': 'icon', 'type': 'image/png', 'sizes': '16x16', 'href': '../img/favicon16.png'}))
    if style_template:
        head.append(style_template)

    # --- Restructure Body ---
    if not soup.body:
        soup.html.append(soup.new_tag('body'))
        
    body = soup.body
    new_body = soup.new_tag('body')

    # Process images
    if body:
        for img in body.find_all('img'):
            if not img.has_attr('src'):
                print(f"    - Skipping image with no src attribute.")
                continue

            figure = soup.new_tag('figure')
            img_clone = soup.new_tag('img', attrs={'src': img['src'], 'alt': img.get('alt', '')})
            figure.append(img_clone)
            
            print(f"    - Processing image: {img['src']}")

            figcaption = soup.new_tag('figcaption')
            img_parent_p = img.find_parent('p')

            if img_parent_p and img_parent_p.find_next_sibling('p'):
                next_p = img_parent_p.find_next_sibling('p')
                caption_parts = []
                source_link_tag = None

                while next_p:
                    link = next_p.find('a')
                    if link and link.has_attr('href') and link['href'] != 'about:blank':
                        source_text_p = next_p.find_previous_sibling('p')
                        source_text = "Source"
                        if source_text_p and 'Source' in source_text_p.get_text():
                            source_text = source_text_p.get_text(strip=True)
                            source_text_p.extract()
                        
                        source_link_tag = soup.new_tag('a', attrs={'href': link['href']})
                        source_link_tag.string = source_text
                        next_p.extract()
                        break
                    
                    if next_p.get('align') == 'justify': 
                        break
                    
                    caption_parts.append(next_p.get_text(strip=True))
                    current_p = next_p
                    next_p = next_p.find_next_sibling('p')
                    current_p.extract()

                if caption_parts:
                    figcaption.append(' '.join(caption_parts))
                if source_link_tag:
                    figcaption.append(soup.new_tag('br'))
                    figcaption.append(source_link_tag)
                
                if figcaption.contents:
                    figure.append(figcaption)
                
                img_parent_p.extract()
            
            new_body.append(figure)

    # Process main text
    main_text_div = soup.new_tag('div', attrs={'class': 'main-text'})
    if body:
        for p in body.find_all('p', {'align': 'justify'}):
            main_text_div.append(p.extract())
    if main_text_div.contents:
        new_body.append(main_text_div)

    # Process references
    if body:
        ref_start = body.find(lambda tag: tag.name == 'p' and 'References' in tag.get_text())
        if ref_start:
            references_div = soup.new_tag('div', attrs={'class': 'references-section'})
            references_header = soup.new_tag('h2')
            references_header.string = "Références"
            references_div.append(references_header)
            
            ref_p = ref_start.find_next_sibling('p')
            while ref_p:
                for attr in list(ref_p.attrs):
                    del ref_p[attr]
                references_div.append(ref_p.extract())
                ref_p = ref_p.find_next_sibling('p')
            
            ref_start.extract()
            
            if len(references_div.contents) > 1:
                new_body.append(references_div)

    soup.body.replace_with(new_body)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))
    print(f"    - Successfully wrote formatted file.")

def main():
    try:
        style = get_template_style()
    except FileNotFoundError:
        print(f"ERROR: Template file '{TEMPLATE_FILE}' not found.")
        return

    for filename in os.listdir(DETAILS_DIR):
        if filename.endswith('.html') and filename not in FILES_TO_IGNORE:
            file_path = os.path.join(DETAILS_DIR, filename)
            print(f"Formatting {file_path}...")
            try:
                format_html_file(file_path, style)
                print(f" -> SUCCESS")
            except Exception as e:
                print(f" -> FAILURE: {e}")

if __name__ == '__main__':
    main()