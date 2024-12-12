from jinja2 import Template

hostname_wg = Template(
    """
{% if rdomain is defined %}
rdomain {{ rdomain }}

{% endif %}
inet {{ inet }}
inet6 {{ inet6 }}

mtu {{ mtu | default(1420) }}
up

wgkey {{ wgkey }}
wgport {{ wgport }}

wgpeer {{ peer_pubkey }}{% if peer_psk is defined %} wgpsk {{ peer_psk }}{% endif %} wgendpoint {{ peer_ip }} {{ peer_port }}{% if peer_aip4 is defined %} wgaip {{ peer_aip4 }}{% endif %}{% if peer_aip6 is defined %} wgaip {{ peer_aip6 }}{% endif %} wgaip 172.20.0.0/14 wgaip fd00::/8

{% if peer_ll4 is defined %}
!route -n -T {{ rdomain }} add -inet -iface {{ peer_ll4 }} {{ inet }}
{% endif %}
{% if peer_ll6 is defined %}
!route -n -T {{ rdomain }} add -inet6 {{ peer_ll6 }} {{ inet6 }}%wg{{ wgid }}
{% endif %}
!route -n -T {{ rdomain }} sourceaddr -ifp lo{{ rdomain }}
"""
)

bgpd_peer_macros = Template(
    """
{% for peer in peers %}
P{{ loop.index }}_descr="{{ peer.description }}"
P{{ loop.index }}_remote4="{{ peer.dn42_ip4 }}"
P{{ loop.index }}_remote6="{{ peer.dn42_ip6 }}"
P{{ loop.index }}_asn="{{ peer.asn }}"

{% endfor %}
"""
)

bgpd_peer_group = Template(
    """
group "dn42_peers" {
        announce IPv4 unicast
        announce IPv6 unicast
{% for peer in peers %}
{% if peer.ip4 is defined %}
        neighbor $P{{ loop.index }}_remote4 {
                remote-as $P{{ loop.index }}_asn
                descr $P{{ loop.index }}_descr
                set nexthop $P{{ loop.index }}_remote4
        }
{% endif %}
{% if peer.ip6 is defined %}
        neighbor $P{{ loop.index }}_remote6 {
                remote-as $P{{ loop.index }}_asn
                descr $P{{ loop.index }}_descr
                set nexthop $P{{ loop.index }}_remote6
        }
{% endif %}
{% endfor %}
}
"""
)
