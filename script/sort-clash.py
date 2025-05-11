import sys
import re
import asyncio


def clean_line(line):
    """
    清理行中的无意义字符（包括空格、引号、特殊符号）
    """
    return line.replace(" ", "").replace("-", "").replace('"', "").replace("'", "").replace("|", "").replace("^", "")


def is_valid_domain(domain):
    """
    检查是否为合法的纯域名或域名后缀
    仅保留符合条件的域名，例如：
    - example.com (纯域名)
    - .com (域名后缀)
    """
    # 匹配纯域名或域名后缀
    domain_pattern = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$|^\.[a-zA-Z]{2,}$")
    return bool(domain_pattern.match(domain))


def extract_domain(line):
    """
    从规则中提取有效域名，允许的格式为：
    - 'DOMAIN,domain'
    - 'DOMAIN-SUFFIX,domain'
    - '+.domain'
    - '*.domain'
    - '.domain'
    - 纯域名
    """
    line = clean_line(line.strip())
    if not line or line.startswith((
        "payload:", "rules:", "IP-CIDR,", "DOMAIN-KEYWORD,", "PROCESS-NAME,", "IP-SUFFIX,", "GEOIP,", "GEOSITE,", "#", "!", "/", "【", "】", "[", "]"
    )):
        return None

    if line.startswith("DOMAIN,"):
        domain = line[7:]
    elif line.startswith("DOMAIN-SUFFIX,"):
        domain = line[14:]
    elif line.startswith("+."):
        domain = line[2:]
    elif line.startswith("*"):
        domain = line[1:]
    elif line.startswith("."):
        domain = line[1:]
    elif "." in line:
        domain = line
    else:
        return None

    return domain if is_valid_domain(domain) else None


async def process_chunk(chunk):
    """
    异步处理文件块，提取域名规则
    """
    domains = set()
    for line in chunk:
        domain = extract_domain(line)
        if domain:
            domains.add(domain)
    return domains


async def read_lines(file_path):
    """
    异步逐行读取文件
    """
    with open(file_path, "r", encoding="utf8") as f:
        while True:
            lines = f.readlines(10000)  # 每次读取 10KB
            if not lines:
                break
            yield lines


def remove_subdomains(domains):
    """
    移除子域名，只保留父域名
    """
    sorted_domains = sorted(domains, key=lambda d: d[::-1])  # 按域名倒序排序
    result = []
    for domain in sorted_domains:
        if not result or not domain.endswith("." + result[-1]):  # 当前域名不是上一个域名的子域名
            result.append(domain)
    return set(result)


async def main():
    if len(sys.argv) < 2:
        print("请提供输入文件路径作为参数")
        return

    file_name = sys.argv[1]

    # 按块处理文件
    domains = set()

    async for chunk in read_lines(file_name):
        chunk_domains = await process_chunk(chunk)
        domains.update(chunk_domains)

    # 移除子域名，保留父域名
    filtered_domains = remove_subdomains(domains)

    # 排序规则：按父域名和子域名排序
    sorted_domains = sorted(filtered_domains)

    # 写入文件
    with open(file_name, "w", encoding="utf8") as f:
        f.writelines(f"{domain}\n" for domain in sorted_domains)

    print(f"处理完成，生成的规则总数为：{len(sorted_domains)}")


if __name__ == "__main__":
    asyncio.run(main())
