import os

from . import logger


class DN42:

    @staticmethod
    def aut_num(registry: str, asn: int) -> str:
        # check if registry is a directory
        if not os.path.isdir(registry):
            raise RuntimeError(f"Registry {registry} is not a directory")

        # check that the aut-num directory exists
        aut_num = os.path.join(registry, f"data/aut-num")
        if not os.path.isdir(aut_num):
            raise RuntimeError(f"aut-num directory {aut_num} does not exist")

        # check that ASN file exists
        asn_file = os.path.join(aut_num, f"AS{asn}")
        if not os.path.isfile(asn_file):
            raise RuntimeError(f"ASN file {asn_file} does not exist")

        return asn_file

    @staticmethod
    def person(registry: str, asn: int) -> str:
        asn_file = DN42.aut_num(registry, asn)

        # read the file and return the tech-c object
        with open(asn_file) as f:
            for line in f:
                if line.startswith("tech-c:"):
                    techc = line.split()[1]
                    break
            else:
                raise RuntimeError(f"tech-c not found in {asn_file}")
        logger.debug("ASN %d tech-c is %s", asn, techc)

        # check that tech-c is a person object
        person_file = os.path.join(registry, f"data/person/{techc}")
        if not os.path.isfile(person_file):
            raise RuntimeError(f"Person file {person_file} does not exist")
        return person_file

    @staticmethod
    def email(registry: str, asn: int) -> str:
        person_file = DN42.person(registry, asn)

        # read the file and return the email object
        with open(person_file) as f:
            for line in f:
                if line.startswith("e-mail:"):
                    email = line.split()[1]
                    logger.debug("ASN %d email is %s", asn, email)
                    return email
        raise RuntimeError(f"Email not found in {person_file}")

    @staticmethod
    def mntner(registry: str, asn: int) -> str:
        asn_file = DN42.aut_num(registry, asn)

        with open(asn_file) as f:
            for line in f:
                if line.startswith("mnt-by:"):
                    mntner = line.split()[1]
                    break
            else:
                raise RuntimeError(f"mntner not found in {asn_file}")
        logger.debug("ASN %d mntner is %s", asn, mntner)

        mntner_file = os.path.join(registry, f"data/mntner/{mntner}")
        if not os.path.isfile(mntner_file):
            raise RuntimeError(f"mntner file {mntner_file} does not exist")

        return mntner_file

    @staticmethod
    def pgp_fingerprint(registry: str, asn: int) -> str:
        mnt_file = DN42.mntner(registry, asn)

        # read the file and return the pubkey object
        with open(mnt_file) as f:
            for line in f:
                if line.startswith("auth:"):
                    auth_type = line.split()[1]
                    if auth_type == "pgp-fingerprint":
                        fingerprint = line.split()[2]
                        logger.debug("ASN %d fingerprint is %s", asn, fingerprint)
                        return fingerprint
        raise RuntimeError(f"PGP fingerprint not found in {mnt_file}")
