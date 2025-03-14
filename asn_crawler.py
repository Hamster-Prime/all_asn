import requests
from bs4 import BeautifulSoup
import re
import time
import argparse
import os

def extract_as_numbers(html_content):

    soup = BeautifulSoup(html_content, 'html.parser')

    as_links = soup.select('td.table-cell a[href^="/AS"]')

    as_numbers = []
    for link in as_links:
        as_text = link.text
        if as_text.startswith('AS'):
            as_number = as_text[2:]
            as_numbers.append(as_number)
    
    return as_numbers

def get_total_pages(html_content):

    soup = BeautifulSoup(html_content, 'html.parser')

    pagination_text = None
    pagination_spans = soup.select('.pagination span')
    
    for span in pagination_spans:
        if "总共" in span.text:
            pagination_text = span.text
            break
    
    if pagination_text:

        total_match = re.search(r'总共(\d+)条', pagination_text)
        if total_match:
            total_records = int(total_match.group(1))
            records_per_page = 1000
            total_pages = (total_records + records_per_page - 1) // records_per_page
            return total_pages

    next_page_link = soup.select_one('.pagination a:not([disabled])')
    if next_page_link and '>' in next_page_link.text:
        href = next_page_link.get('href', '')
        match = re.search(r'/(\d+)$', href)
        if match:
            return int(match.group(1))

    return 1

def ensure_rsc_extension(filename, country_code):

    if filename != 'asn_list.rsc':
        base_name = os.path.splitext(filename)[0]
        return f"{base_name}.rsc"

    return f"{country_code.upper()}_ASN.rsc"

def crawl_asn_info(base_url, country_code, output_file, start_page=1, end_page=None, delay=1):
    all_as_numbers = []
    url = f"{base_url}/countries/{country_code}/{start_page}"
    if start_page == 1:
        url = f"{base_url}/countries/{country_code}"
    
    print(f"获取页面: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"获取页面失败: {url}, 状态码: {response.status_code}")
        return

    if end_page is None:
        total_pages = get_total_pages(response.text)
        end_page = total_pages
        print(f"检测到总页数: {total_pages}")

    as_numbers = extract_as_numbers(response.text)
    all_as_numbers.extend(as_numbers)
    print(f"页面 {start_page} 提取了 {len(as_numbers)} 个AS号")

    for page in range(start_page + 1, end_page + 1):
        page_url = f"{base_url}/countries/{country_code}/{page}"
        print(f"获取页面: {page_url}")

        time.sleep(delay)
        
        try:
            response = requests.get(page_url, headers=headers)
            if response.status_code != 200:
                print(f"获取页面失败: {page_url}, 状态码: {response.status_code}")
                continue
            
            as_numbers = extract_as_numbers(response.text)
            all_as_numbers.extend(as_numbers)
            print(f"页面 {page} 提取了 {len(as_numbers)} 个AS号")
        except Exception as e:
            print(f"处理页面 {page_url} 时出错: {str(e)}")

    output_file = ensure_rsc_extension(output_file, country_code)

    list_name = f"{country_code.upper()}_ASN"  # 例如 CN_ASN, HK_ASN 等
    with open(output_file, 'w') as f:
        f.write(f'/log info "Loading {country_code.upper()} ASN list"\n')
        f.write('/routing filter num-list\n')

        for as_number in all_as_numbers:
            f.write(f':do {{ add list={list_name} range={as_number} }} on-error={{}}\n')
    
    print(f"总共提取了 {len(all_as_numbers)} 个AS号，已保存到 {output_file}")

def main():
    parser = argparse.ArgumentParser(description='爬取指定国家/地区的ASN信息')
    parser.add_argument('--country', type=str, default='us', help='国家/地区代码，例如：us, cn, jp等')
    parser.add_argument('--output', type=str, default='asn_list.rsc', help='输出文件路径')
    parser.add_argument('--start', type=int, default=1, help='起始页码')
    parser.add_argument('--end', type=int, help='结束页码，不指定则爬取所有页')
    parser.add_argument('--delay', type=float, default=1.0, help='请求间隔时间(秒)')
    parser.add_argument('--base', type=str, default='https://www.pdflibr.com', help='基础URL')
    
    args = parser.parse_args()
    
    crawl_asn_info(args.base, args.country, args.output, args.start, args.end, args.delay)

if __name__ == "__main__":
    main()
