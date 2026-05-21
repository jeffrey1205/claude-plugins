#!/bin/bash
# 网络/转发专项采集脚本
# 用法: ./collect_network.sh [duration_seconds]
# 输出: 纯文本，便于复制粘贴

DURATION=${1:-10}

echo "=========================================="
echo "网络/转发专项采集"
echo "时长: ${DURATION}s"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 网卡统计
echo ""
echo "--- 网卡统计 ---"
cat /proc/net/dev

# 网卡详细统计（ethtool）
echo ""
echo "--- 网卡详细统计 ---"
for iface in $(ls /sys/class/net/ 2>/dev/null | grep -v lo); do
    echo "接口: $iface"
    if command -v ethtool >/dev/null 2>&1; then
        ethtool -S $iface 2>/dev/null | head -20
    else
        echo "  ethtool 不可用"
    fi
    echo ""
done

# 网卡队列信息
echo ""
echo "--- 网卡队列信息 ---"
for iface in $(ls /sys/class/net/ 2>/dev/null | grep -v lo); do
    echo "接口: $iface"
    echo "  RX 队列数: $(ls /sys/class/net/$iface/queues/ 2>/dev/null | grep rx | wc -l)"
    echo "  TX 队列数: $(ls /sys/class/net/$iface/queues/ 2>/dev/null | grep tx | wc -l)"

    # RPS/RFS 配置
    for rxq in /sys/class/net/$iface/queues/rx-*/rps_cpus; do
        if [ -f "$rxq" ]; then
            echo "  RPS: $(cat $rxq)"
        fi
    done
    echo ""
done

# softnet_stat
echo ""
echo "--- softnet_stat ---"
cat /proc/net/softnet_stat
echo ""
echo "字段含义: 已处理 | dropped | time_squeeze | ..."

# 中断分布
echo ""
echo "--- 中断分布 ---"
cat /proc/interrupts | head -1
cat /proc/interrupts | grep -i -E "(eth|net|ixgbe|i40e|mlx)" | head -10

# 中断亲和性
echo ""
echo "--- 中断亲和性 ---"
for irq_dir in /proc/irq/*/; do
    irq_num=$(basename $irq_dir)
    if [ -f "$irq_dir/smp_affinity" ]; then
        affinity=$(cat $irq_dir/smp_affinity 2>/dev/null)
        # 只显示有网络中断的
        if [ -f "$irq_dir/actions" ]; then
            actions=$(cat $irq_dir/actions 2>/dev/null)
            if echo "$actions" | grep -q -i -E "(eth|net|ixgbe|i40e|mlx)"; then
                echo "IRQ $irq_num ($actions): $affinity"
            fi
        fi
    fi
done

# Socket 统计
echo ""
echo "--- Socket 统计 ---"
if command -v ss >/dev/null 2>&1; then
    echo "TCP 连接状态:"
    ss -s 2>/dev/null
else
    echo "ss 不可用，使用 /proc/net/tcp"
    echo "TCP 连接数: $(cat /proc/net/tcp 2>/dev/null | wc -l)"
    echo "TCP6 连接数: $(cat /proc/net/tcp6 2>/dev/null | wc -l)"
fi

# 协议统计
echo ""
echo "--- 协议统计 ---"
echo "SNMP 统计:"
cat /proc/net/snmp 2>/dev/null | grep -E "^(Tcp|Udp|Ip):" | head -10

echo ""
echo "netstat 统计:"
cat /proc/net/netstat 2>/dev/null | head -5

# 网络采样
echo ""
echo "--- 网络采样 (${DURATION}秒) ---"
echo "时间戳 接口 RX_packets RX_bytes TX_packets TX_bytes"

for i in $(seq 1 $DURATION); do
    cat /proc/net/dev | grep -v lo | grep -v face | while read -r NET_LINE; do
        IFACE=$(echo "$NET_LINE" | awk -F: '{print $1}' | xargs)
        STATS=$(echo "$NET_LINE" | awk -F: '{print $2}')
        RX_PACKETS=$(echo $STATS | awk '{print $2}')
        RX_BYTES=$(echo $STATS | awk '{print $1}')
        TX_PACKETS=$(echo $STATS | awk '{print $10}')
        TX_BYTES=$(echo $STATS | awk '{print $9}')
        echo "$(date '+%H:%M:%S') $IFACE $RX_PACKETS $RX_BYTES $TX_PACKETS $TX_BYTES"
    done
    sleep 1
done

# conntrack（如果可用）
echo ""
echo "--- conntrack ---"
if [ -f "/proc/net/nf_conntrack" ]; then
    echo "连接跟踪数: $(cat /proc/net/nf_conntrack 2>/dev/null | wc -l)"
    echo "连接跟踪最大值: $(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null)"
elif [ -f "/proc/sys/net/ipv4/netfilter/ip_conntrack_max" ]; then
    echo "连接跟踪最大值: $(cat /proc/sys/net/ipv4/netfilter/ip_conntrack_max 2>/dev/null)"
else
    echo "conntrack 不可用或无权限"
fi

# 网络栈参数
echo ""
echo "--- 网络栈参数 ---"
echo "net.core.rmem_max: $(cat /proc/sys/net/core/rmem_max 2>/dev/null)"
echo "net.core.wmem_max: $(cat /proc/sys/net/core/wmem_max 2>/dev/null)"
echo "net.core.netdev_max_backlog: $(cat /proc/sys/net/core/netdev_max_backlog 2>/dev/null)"
echo "net.core.somaxconn: $(cat /proc/sys/net/core/somaxconn 2>/dev/null)"
echo "net.ipv4.tcp_max_syn_backlog: $(cat /proc/sys/net/ipv4/tcp_max_syn_backlog 2>/dev/null)"

echo ""
echo "=========================================="
echo "采集完成"
echo "=========================================="
