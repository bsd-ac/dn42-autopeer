from jinja2 import Template

hostname_wg = Template(
    """
rdomain {{ rdomain }}

inet {{ inet }}
inet6 {{ inet6 }}

mtu {{ mtu }}
up

wgkey {{ wgkey }}
wgport {{ wgport }}

wgpeer {{ peer_pubkey }} wgendpoint {{ peer_ip }} {{ peer_port }} wgaip {{ peer_aip }} wgaip 172.20.0.0/14 wgaip fd00::/8

!route -n -T {{ rdomain }} add -inet -iface {{ peer_ll4 }} {{ inet }}
!route -n -T {{ rdomain }} add -inet6 {{ peer_ll6 }} {{ inet6 }}%wg{{ wgid }}
!route -n -T {{ rdomain }} sourceaddr -ifp lo{{ rdomain }}
"""
)

bgpd_conf = Template(
    """
###
# macros
ASN="{{ ASN }}"

{% for peer in peers %}
P{{ loop.index }}_descr="{{ peer.asn }}.{{ peer.description }}"
P{{ loop.index }}_remote4="{{ peer.dn42_ip4 }}"
P{{ loop.index }}_remote6="{{ peer.dn42_ip6 }}"
P{{ loop.index }}_asn="{{ peer.asn }}"

{% endfor %}
###
# global configuration
AS $ASN
router-id {{ BGP_ROUTER_ID }}

listen on {{ BGP_ROUTER_ID }} port 179
{% for peer in peers %}
listen on {{ peer.ll_ip4 }} port 179
listen on {{ peer.ll_ip6 }} port 179
{% endfor %}

socket "/var/www/run/bgpd.rsock" restricted

log updates

nexthop qualify via default

dump table-v2 "/tmp/rib-dump-%H%M" 30

###
# set configuration
prefix-set mynetworks {
        172.22.109.96/27
        fd5e:e6ff:d44::4242/48
}

prefix-set dn42 {
        172.20.0.0/14
        fd00::/8
}

include "/var/db/dn42/roa-obgp.conf"

###
# network and flowspec announcements

# Generate routes for the networks our ASN will originate.
# The communities (read 'tags') are later used to match on what
# is announced to EBGP neighbors
network prefix-set mynetworks set large-community $ASN:1:1

###
# neighbors and groups
group "dn42_peers" {
        announce IPv4 unicast
        announce IPv6 unicast
{% for peer in peers %}
        neighbor $P{{ loop.index }}_remote6 {
                remote-as $P{{ loop.index }}_asn
                descr $P{{ loop.index }}_descr
                set nexthop $P{{ loop.index }}_remote6
        }
{% endfor %}
}

###
# filters

# deny more-specifics of our own originated prefixes
deny quick from ebgp prefix-set mynetworks or-longer

# filter out too long paths
deny quick from any max-as-len 8

# don't need non-dn42 routes
#deny quick from ebgp prefix-set dn42 or-longer

# Outbound EBGP: only allow self originated networks to ebgp peers
allow to ebgp prefix-set mynetworks large-community $ASN:1:1

# Allow validated routes to peers
allow to ebgp ovs valid

# Allow validated routes from peers
allow from ebgp ovs valid

# IBGP: allow all updates to and from our IBGP neighbors
allow from ibgp
allow to ibgp

# Scrub normal and large communities relevant to our ASN from EBGP neighbors
# https://tools.ietf.org/html/rfc7454#section-11
match from ebgp set { large-community delete $ASN:*:* }

# Honor requests to gracefully shutdown BGP sessions
# https://tools.ietf.org/html/rfc8326
match from any community GRACEFUL_SHUTDOWN set { localpref 0 }
"""
)
