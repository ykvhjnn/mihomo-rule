#!/bin/bash

# 切换到脚本所在目录
cd $(cd "$(dirname "$0")";pwd)

# 定义日志函数
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $@"
}

error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $@" >&2
}

# 定义规则源和对应的处理脚本
declare -A RULES=(
    [Ad]="sort-adblock.py
        https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.plus.mini.txt
        https://raw.githubusercontent.com/ghvjjjj/adblockfilters/main/rules/adblockdnslite.txt
        https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.xiaomi.txt
        https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.oppo-realme.txt
    "
    [Proxy]="sort-clash.py
        https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/tld-proxy.list
        https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/proxy.list
        https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/Proxy/Proxy_Domain_For_Clash.txt
        https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/refs/heads/release/gfw.txt
    "
    [Direct]="sort-clash.py
        https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/cn.txt
        https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/cn.list
        https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/refs/heads/release/direct.txt
    "
)

# 函数：修复 URL 协议
fix_url_protocol() {
    local url=$1
    echo "$url" | sed 's/^ttps:/https:/'
}

# 函数：处理规则
process_rules() {
    local name=$1
    local script=$2
    shift 2
    local urls=("$@")
    local domain_file="${name}_domain.txt"
    local tmp_file="${name}_tmp.txt"
    local white_file="${name}_white.txt"
    local final_file="${name}_final.txt"

    log "开始处理规则: $name"

    # 初始化文件
    > "$domain_file"
    > "$white_file"
    > "$tmp_file"

    # 分类下载规则到对应的文件
    local has_white=0
    for url in "${urls[@]}"; do
        # 修复错误的 URL 协议头
        url=$(fix_url_protocol "$url")

        if [[ "$url" == [white]* ]]; then
            has_white=1
            url="${url#[white]}"
            if ! curl --http2 --compressed --max-time 30 --retry 3 -sSL "$url" >> "$white_file"; then
                error "白名单规则下载失败: $url"
            fi
        else
            if ! curl --http2 --compressed --max-time 30 --retry 3 -sSL "$url" >> "$tmp_file"; then
                error "规则下载失败: $url"
            fi
        fi
    done

    log "规则文件下载完成: $name"

    if [[ $has_white -eq 1 ]]; then
        # 合并并去重白名单
        sort -u "$white_file" -o "$white_file"
        log "白名单已合并去重: $white_file"

        # 合并并去重正常清单
        sort -u "$tmp_file" -o "$tmp_file"
        log "正常清单已合并去重: $tmp_file"

        # 从正常清单移除与白名单重复的条目
        comm -23 "$tmp_file" "$white_file" > "$final_file"
        log "已从正常清单移除与白名单重复条目: $final_file"

        # 删除临时文件
        rm -f "$tmp_file" "$white_file"
    else
        # 如果没有白名单，只需直接合并去重正常清单
        sort -u "$tmp_file" -o "$final_file"
        log "正常清单已合并去重: $final_file"

        # 删除临时文件
        rm -f "$tmp_file"
    fi

    # 修复换行符并调用对应的 Python 脚本去重排序
    sed -i 's/\r//' "$final_file"
    python "$script" "$final_file"
    if [ $? -ne 0 ]; then
        error "Python 脚本执行失败: $script"
        return 1
    fi
    log "Python 脚本执行完成: $script"

    # 转换为 Mihomo 格式
    sed "s/^/\\+\\./g" "$final_file" > "${name}_Mihomo.txt"
    log "Mihomo 格式转换完成: ${name}_Mihomo.txt"
}

# 下载 Mihomo 工具
setup_mihomo_tool() {
    log "开始下载 Mihomo 工具"
    wget -q https://github.com/MetaCubeX/mihomo/releases/download/Prerelease-Alpha/version.txt
    if [ $? -ne 0 ]; then
        error "下载版本文件失败"
        exit 1
    fi

    version=$(cat version.txt)
    mihomo_tool="mihomo-linux-amd64-$version"

    wget -q "https://github.com/MetaCubeX/mihomo/releases/download/Prerelease-Alpha/$mihomo_tool.gz"
    if [ $? -ne 0 ]; then
        error "下载 Mihomo 工具失败"
        exit 1
    fi

    gzip -d "$mihomo_tool.gz"
    chmod +x "$mihomo_tool"
    log "Mihomo 工具下载完成: $mihomo_tool"
}

# 主流程
setup_mihomo_tool

# 逐组处理规则
for name in "${!RULES[@]}"; do
    # 解析规则配置
    IFS=$'\n' read -r -d '' script urls <<< "${RULES[$name]}"
    urls=($urls) # 转为数组
    process_rules "$name" "$script" "${urls[@]}"
done

# 清理缓存文件
rm -rf ./*.txt "$mihomo_tool"
log "脚本执行完成，已清理临时文件"
