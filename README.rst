=====================
Auto Peering for DN42
=====================

Program to set up an auto peering service for DN42 on OpenBSD.

Installation
------------

.. code:: bash

    pip install dn42-autopeer


Usage
-----

.. code:: bash

    $ autopeer -f /etc/autopeer.conf


Autopeer
--------

Anyone can request to peer with your ASN by sending a POST request to the appropriate endpoint.
The request must be signed with their GPG key, the autopeer server will verify the signature and add the peer to the list.
The signature is verified by fetching the GPG key for the email registered by the user in the DN42 registry.

.. code:: bash

    $ cat request.json | gpg --sign --detach-sig - | base64 -w 0 > request.sig
    $ curl -w '\n' -X POST -d @request.json \
        -H "Content-Type: application/json" \
        -H "X-DN42-Signature: $(cat request.sig)" \
        -H "X-DN42-ASN: 4242420000" \
        https://dn42-sea.bsd.ac/autopeer
