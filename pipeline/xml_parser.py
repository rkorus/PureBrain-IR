"""Parse 13F information table XML into structured holdings data.

13F XML structure (from SEC schema):
  <informationTable>
    <infoTable>
      <nameOfIssuer>COMPANY NAME</nameOfIssuer>
      <titleOfClass>COM</titleOfClass>
      <cusip>XXXXXXXXX</cusip>
      <value>123456</value>  <!-- in thousands of USD -->
      <shrsOrPrnAmt>
        <sshPrnamt>123456</sshPrnamt>
        <sshPrnamtType>SH</sshPrnamtType>  <!-- SH or PRN -->
      </shrsOrPrnAmt>
      <investmentDiscretion>SOLE|DFND|OTR</investmentDiscretion>
      <otherManager>1</otherManager>
      <votingAuthority>
        <Sole>123456</Sole>
        <Shared>0</Shared>
        <None>0</None>
      </votingAuthority>
    </infoTable>
    ...
  </informationTable>
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass


# SEC 13F namespace
NS = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}


@dataclass
class Holding:
    """Single holding from a 13F information table."""
    name_of_issuer: str
    title_of_class: str
    cusip: str
    value_thousands: int  # reported in thousands of USD
    shares: int
    shares_type: str  # SH (shares) or PRN (principal amount)
    investment_discretion: str  # SOLE, DFND, OTR
    voting_sole: int
    voting_shared: int
    voting_none: int


def parse_info_table(xml_bytes: bytes) -> list[Holding]:
    """Parse 13F information table XML into list of Holdings.

    Handles both namespaced and non-namespaced XML.
    """
    root = ET.fromstring(xml_bytes)

    # Try namespaced first, fall back to non-namespaced
    entries = root.findall("ns:infoTable", NS)
    if not entries:
        entries = root.findall("infoTable")
    if not entries:
        # Try with different namespace patterns
        for child in root:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "infoTable":
                entries = [c for c in root if c.tag == child.tag]
                break

    holdings = []
    for entry in entries:
        holding = _parse_entry(entry)
        if holding:
            holdings.append(holding)

    return holdings


def _get_text(element, tag: str, ns_tag: str | None = None) -> str:
    """Get text from child element, trying namespaced then non-namespaced."""
    if ns_tag:
        el = element.find(ns_tag, NS)
        if el is not None and el.text:
            return el.text.strip()
    el = element.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    # Try with namespace prefix in tag itself
    for child in element:
        child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if child_tag == tag:
            return (child.text or "").strip()
    return ""


def _get_int(element, tag: str, ns_tag: str | None = None) -> int:
    """Get integer from child element."""
    text = _get_text(element, tag, ns_tag)
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _parse_entry(entry) -> Holding | None:
    """Parse single infoTable entry into Holding."""
    name = _get_text(entry, "nameOfIssuer", "ns:nameOfIssuer")
    if not name:
        return None

    title = _get_text(entry, "titleOfClass", "ns:titleOfClass")
    cusip = _get_text(entry, "cusip", "ns:cusip")
    value = _get_int(entry, "value", "ns:value")

    # Shares or principal amount
    shares = 0
    shares_type = "SH"
    shr_el = entry.find("ns:shrsOrPrnAmt", NS)
    if shr_el is None:
        shr_el = entry.find("shrsOrPrnAmt")
    if shr_el is None:
        for child in entry:
            if child.tag.split("}")[-1] == "shrsOrPrnAmt":
                shr_el = child
                break
    if shr_el is not None:
        shares = _get_int(shr_el, "sshPrnamt", "ns:sshPrnamt")
        shares_type = _get_text(shr_el, "sshPrnamtType", "ns:sshPrnamtType") or "SH"

    discretion = _get_text(entry, "investmentDiscretion", "ns:investmentDiscretion")

    # Voting authority
    vote_sole = vote_shared = vote_none = 0
    vote_el = entry.find("ns:votingAuthority", NS)
    if vote_el is None:
        vote_el = entry.find("votingAuthority")
    if vote_el is None:
        for child in entry:
            if child.tag.split("}")[-1] == "votingAuthority":
                vote_el = child
                break
    if vote_el is not None:
        vote_sole = _get_int(vote_el, "Sole", "ns:Sole")
        vote_shared = _get_int(vote_el, "Shared", "ns:Shared")
        vote_none = _get_int(vote_el, "None", "ns:None")

    return Holding(
        name_of_issuer=name,
        title_of_class=title,
        cusip=cusip,
        value_thousands=value,
        shares=shares,
        shares_type=shares_type,
        investment_discretion=discretion,
        voting_sole=vote_sole,
        voting_shared=vote_shared,
        voting_none=vote_none,
    )


def parse_file(filepath: str) -> list[Holding]:
    """Parse a 13F XML file from disk."""
    with open(filepath, "rb") as f:
        return parse_info_table(f.read())
