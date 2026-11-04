"""The RHEL ISO is checked against the checksums Red Hat publishes."""

from __future__ import annotations

from autorelabel import box

RHEL_10_0 = "edce2dd6f8e1d1b2ff0b204f89b0659bc9e320d175beb7caad60712957a19608"


def test_red_hats_checksum_verifies_the_iso():
    verified, message = box.check_iso(RHEL_10_0, "10.0")
    assert verified is True and "RHEL 10.0" in message


def test_another_checksum_for_a_known_version_is_a_damaged_download():
    verified, message = box.check_iso("0" * 64, "10.0")
    assert verified is False and "doesn't match" in message


def test_a_version_without_a_known_checksum_shows_the_digest_to_compare():
    verified, message = box.check_iso("1" * 64, "10.1")
    assert verified is None and "1" * 64 in message


def test_the_list_holds_only_sha256_digests_of_rhel_10():
    for digest, version in box.RED_HAT_DVD_SHA256.items():
        assert len(digest) == 64 and int(digest, 16) >= 0
        assert version.startswith("10.")
