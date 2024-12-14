from jinja2 import StrictUndefined, Template

hostname_wg = Template(
    undefined=StrictUndefined,
    source="""\
rdomain {{ wg_rdomain }}

inet {{ our_ll_ip4 }}
inet6 {{ our_ll_ip6 }}

mtu {{ wg_mtu }}
up

wgkey {{ wg_privkey }}
wgport {{ wg_port }}

wgpeer {{ peer_pubkey }}{% if peer_psk is defined %} wgpsk {{ peer_psk }}{% endif %}{% if peer_ip is defined %} wgendpoint {{ peer_ip }} {{ peer_port }}{% endif %}{% if peer_ll_ip4 is defined %} wgaip {{ peer_ll_ip4 }}/32{% endif %}{% if peer_ll_ip6 is defined %} wgaip {{ peer_ll_ip6 }}/128{% endif %} wgaip {{ dn42_netspace4 }} wgaip {{ dn42_netspace6 }}

{% if peer_ll_ip4 is defined %}
!route -n -T {{ wg_rdomain }} add -inet -iface {{ peer_ll_ip4 }} {{ our_ll_ip4 }}
{% endif %}
{% if peer_ll_ip6 is defined %}
!route -n -T {{ wg_rdomain }} add -inet6 {{ peer_ll_ip6 }} {{ our_ll_ip6 }}%{{ wg_interface }}
{% endif %}
!route -n -T {{ wg_rdomain }} sourceaddr -ifp lo{{ wg_rdomain }}
""",
)

bgpd_macros = Template(
    undefined=StrictUndefined,
    source="""\
{% for peer in peers %}
P{{ loop.index }}_descr4="P4_{{ peer.description }}"
P{{ loop.index }}_descr6="P6_{{ peer.description }}"
{% if peer.use_ll_ip4 and peer.peer_ll_ip4 is defined %}
P{{ loop.index }}_remote4="{{ peer.peer_ll_ip4 }}"
{% elif peer.dn42_ip4 is defined %}
P{{ loop.index }}_remote4="{{ peer.dn42_ip4 }}"
{% endif %}
{% if peer.use_ll_ip6 and peer.peer_ll_ip6 is defined %}
P{{ loop.index }}_remote6="{{ peer.peer_ll_ip6 }}%wg{{ peer.wg_interface }}"
{% elif peer.dn42_ip6 is defined %}
P{{ loop.index }}_remote6="{{ peer.dn42_ip6 }}"
{% endif %}
P{{ loop.index }}_asn="{{ peer.ASN }}"

{% endfor %}
""",
)

bgpd_group = Template(
    undefined=StrictUndefined,
    source="""\
group "dn42_peers" {
        announce IPv4 unicast
        announce IPv6 unicast
{% for peer in peers %}
{% if peer.peer_ll_ip4 is defined or peer.dn42_ip4 is defined %}
        neighbor $P{{ loop.index }}_remote4 {
                remote-as $P{{ loop.index }}_asn
                descr $P{{ loop.index }}_descr4
                set nexthop $P{{ loop.index }}_remote4
{% if peer.use_ll_ip4 %}
                local-address {{ peer.our_ll_ip4 }}
{% else %}
                local-address {{ router_ip4 }}
{% endif %}
        }
{% endif %}
{% if peer.peer_ll_ip6 is defined or peer.dn42_ip6 is defined %}
        neighbor $P{{ loop.index }}_remote6 {
                remote-as $P{{ loop.index }}_asn
                descr $P{{ loop.index }}_descr6
                set nexthop $P{{ loop.index }}_remote6
{% if peer.use_ll_ip6 %}
                local-address {{ peer.our_ll_ip6 }}%wg{{ peer.wg_interface }}
{% else %}
                local-address {{ router_ip6 }}
{% endif %}
        }
{% endif %}
{% endfor %}
}
""",
)

bgpd_listener = Template(
    undefined=StrictUndefined,
    source="""\
{% for peer in peers %}
{% if peer.use_ll_ip4 %}
listen on {{ peer.our_ll_ip4 }} port 179
{% endif %}
{% if peer.use_ll_ip6 %}
listen on {{ peer.our_ll_ip6 }}%wg{{ peer.wg_interface }} port 179
{% endif %}
{% endfor %}
""",
)
