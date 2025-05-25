import sys
import re
import asyncio

# 需要去除的国家结尾域名列表
REMOVE_TLD = {
    # 亚洲
    ".jp", ".kr", ".in", ".id", ".th", ".sg", ".my", ".ph", ".vn",
    ".pk", ".bd", ".lk", ".np", ".mn", ".uz", ".kz", ".kg", ".bt", ".mv", ".mm",

    # 欧洲
    ".uk", ".de", ".fr", ".it", ".es", ".ru", ".nl", ".be", ".ch", ".at", ".pl",
    ".cz", ".se", ".no", ".fi", ".dk", ".gr", ".pt", ".ie", ".hu", ".ro", ".bg",
    ".sk", ".si", ".lt", ".lv", ".ee", ".is", ".md", ".ua", ".by", ".am", ".ge",

    # 美洲
    ".us", ".ca", ".mx", ".br", ".ar", ".cl", ".co", ".pe", ".ve", ".uy", ".py",
    ".bo", ".ec", ".cr", ".pa", ".do", ".gt", ".sv", ".hn", ".ni", ".jm", ".cu",

    # 非洲
    ".za", ".eg", ".ng", ".ke", ".gh", ".tz", ".ug", ".dz", ".ma", ".tn", ".ly",
    ".ci", ".sn", ".zm", ".zw", ".ao", ".mz", ".bw", ".na", ".rw", ".mw", ".sd",

    # 大洋洲
    ".au", ".nz", ".fj", ".pg", ".sb", ".vu", ".nc", ".pf", ".ws", ".to", ".ki",
    ".tv", ".nr", ".as",

    # 中东
    ".sa", ".ae", ".ir", ".il", ".iq", ".tr", ".sy", ".jo", ".lb", ".om", ".qa",
    ".ye", ".kw", ".bh"
}

def clean_line(line):
    """
    清理行中的无意义字符（包括空格、引号、特殊符号）
    """
    return line.replace(" ", "").replace("-", "").replace('"', "").replace("'", "").replace("|", "").replace("^", "")


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
        "payload:", "rules:", "regexp", "IP-CIDR,", "DOMAIN-KEYWORD,", "PROCESS-NAME,", "IP-SUFFIX,", "GEOIP,", "GEOSITE,", "#", "!", "/", "【", "】", "@", "[", "]"
    )):
        return None

    if line.startswith("DOMAIN,"):
        return line[7:]
    elif line.startswith("DOMAIN-SUFFIX,"):
        return line[14:]
    elif line.startswith("+."):
        return line[2:]
    elif line.startswith("*"):
        return line[1:]
    elif line.startswith("."):
        return line[1:]
    elif "." in line:
        return line
    else:
        return None

def filter_remove_tld(domains):
    """
    过滤掉以指定国家结尾的域名
    例如：xxx.jp 会被去除，但 xxx.jphj 不会被去除
    """
    result = set()
    for domain in domains:
        for tld in REMOVE_TLD:
            if domain.endswith(tld):
                # 必须严格以 .tld 结尾，且前面为主域或子域
                # 确保不是 xx.jphj 这种
                if len(domain) > len(tld) and domain[-len(tld)-1] == '.':
                    break
                if domain.endswith(tld) and (domain == tld[1:] or domain.endswith(tld)):
                    break
                # 如果直接就是如 jp 这种不带点的也排除
                if domain == tld.lstrip('.'):
                    break
        else:
            result.add(domain)
    return result

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

    # 新增：去除指定国家结尾域名
    filtered_domains = filter_remove_tld(filtered_domains)

    # 排序规则：按父域名和子域名排序
    sorted_domains = sorted(filtered_domains)

    # 写入文件
    with open(file_name, "w", encoding="utf8") as f:
        f.writelines(f"{domain}\n" for domain in sorted_domains)

    print(f"处理完成，生成的规则总数为：{len(sorted_domains)}")


if __name__ == "__main__":
    asyncio.run(main())
