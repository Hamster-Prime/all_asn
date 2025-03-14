import requests
from bs4 import BeautifulSoup
import re
import time
import argparse
import os

def extract_as_numbers(html_content):
    """从HTML内容中提取AS号"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有包含AS号的链接
    as_links = soup.select('td.table-cell a[href^="/AS"]')
    
    # 提取AS号（去掉"AS"前缀）
    as_numbers = []
    for link in as_links:
        as_text = link.text
        if as_text.startswith('AS'):
            as_number = as_text[2:]  # 移除'AS'前缀
            as_numbers.append(as_number)
    
    return as_numbers

def get_total_pages(html_content):
    """获取总页数"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 尝试查找分页信息
    pagination_text = None
    pagination_spans = soup.select('.pagination span')
    
    for span in pagination_spans:
        if "总共" in span.text:
            pagination_text = span.text
            break
    
    if pagination_text:
        # 尝试提取总记录数和当前页范围
        total_match = re.search(r'总共(\d+)条', pagination_text)
        if total_match:
            total_records = int(total_match.group(1))
            # 假设每页显示1000条记录（根据实际页面调整）
            records_per_page = 1000
            total_pages = (total_records + records_per_page - 1) // records_per_page
            return total_pages
    
    # 尝试通过下一页按钮判断
    next_page_link = soup.select_one('.pagination a:not([disabled])')
    if next_page_link and '>' in next_page_link.text:
        href = next_page_link.get('href', '')
        match = re.search(r'/(\d+)$', href)
        if match:
            # 下一页是第2页，说明总共有多页
            return int(match.group(1))
    
    # 默认假设只有一页
    return 1

def ensure_rsc_extension(filename, country_code):
    """确保文件名为 XX_ASN.rsc 格式"""
    # 如果用户指定了文件名，则使用用户指定的基础名称
    if filename != 'asn_list.rsc':
        base_name = os.path.splitext(filename)[0]
        return f"{base_name}.rsc"
    
    # 否则，使用国家/地区代码创建文件名
    return f"{country_code.upper()}_ASN.rsc"

def crawl_asn_info(base_url, country_code, output_file, start_page=1, end_page=None, delay=1):
    """爬取指定国家/地区的ASN信息"""
    all_as_numbers = []
    
    # 先获取第一页以确定总页数
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
    
    # 如果未指定结束页，则获取总页数
    if end_page is None:
        total_pages = get_total_pages(response.text)
        end_page = total_pages
        print(f"检测到总页数: {total_pages}")
    
    # 解析第一页
    as_numbers = extract_as_numbers(response.text)
    all_as_numbers.extend(as_numbers)
    print(f"页面 {start_page} 提取了 {len(as_numbers)} 个AS号")
    
    # 处理其余页面
    for page in range(start_page + 1, end_page + 1):
        page_url = f"{base_url}/countries/{country_code}/{page}"
        print(f"获取页面: {page_url}")
        
        # 添加延迟，避免请求过快
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
    
    # 确保输出文件的名称和后缀正确
    output_file = ensure_rsc_extension(output_file, country_code)
    
    # 写入文件，添加头部信息和格式化AS号
    list_name = f"{country_code.upper()}_ASN"  # 例如 CN_ASN, HK_ASN 等
    with open(output_file, 'w') as f:
        # 添加头部信息
        f.write(f'/log info "Loading {country_code.upper()} ASN list"\n')
        f.write('/routing filter num-list\n')
        
        # 写入格式化的AS号，注意前面添加冒号
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
