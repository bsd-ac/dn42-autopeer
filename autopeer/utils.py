import os

from . import logger


class DN42:

    @staticmethod
    def email(registry: str, asn: int) -> str:
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

        # read the file and return the tech-c object
        with open(asn_file) as f:
            for line in f:
                if line.startswith("tech-c:"):
                    techc = line.split()[1]
                    break
        logger.debug("ASN %d tech-c is %s", asn, techc)

        # check that tech-c is a person object
        person_file = os.path.join(registry, f"data/person/{techc}")
        if not os.path.isfile(person_file):
            raise RuntimeError(f"Person file {person_file} does not exist")

        # read the file and return the email object
        with open(person_file) as f:
            for line in f:
                if line.startswith("e-mail:"):
                    email = line.split()[1]
                    logger.debug("ASN %d email is %s", asn, email)
                    return email
        raise RuntimeError(f"Email not found in {person_file}")
