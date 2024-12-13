from jinja2 import Template

hostname_wg = Template(
    """
rdomain {{ wg_rdomain }}

inet {{ wg_ip4 }}
inet6 {{ wg_ip6 }}

mtu {{ wg_mtu }}
up

wgkey {{ wg_privkey }}
wgport {{ wg_port }}

wgpeer {{ peer_pubkey }}{% if peer_psk is defined %} wgpsk {{ peer_psk }}{% endif %}{% if peer_ip is defined %} wgendpoint {{ peer_endpoint_ip }} {{ peer_endpoint_port }}{% endif %}{% if peer_ip4 is defined %} wgaip {{ peer_ip4 }}/32{% endif %}{% if peer_ip6 is defined %} wgaip {{ peer_ip6 }}/128{% endif %} wgaip {{ dn42_ip4 }} wgaip {{ dn42_ip6 }}

{% if peer_ip4 is defined %}
!route -n -T {{ rdomain }} add -inet -iface {{ peer_ip4 }} {{ wg_ip4 }}
{% endif %}
{% if peer_ip6 is defined %}
!route -n -T {{ rdomain }} add -inet6 {{ peer_ip6 }} {{ wg_ip6 }}%wg{{ wg_interface }}
{% endif %}
!route -n -T {{ rdomain }} sourceaddr -ifp lo{{ wg_rdomain }}
"""
)

bgpd_peer_macros = Template(
    """
{% for peer in peers %}
P{{ loop.index }}_descr="{{ peer.description }}"
{% if peer.dn42_ip4 is defined %}
P{{ loop.index }}_remote4="{{ peer.dn42_ip4 }}"
{% endif %}
{% if peer.dn42_ip6 is defined %}
P{{ loop.index }}_remote6="{{ peer.dn42_ip6 }}"
{% endif %}
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
