"""Describe heat-lot differences; callers enforce specs and unique associations."""
from .matching import heat_valid, norm


def single_heat_difference(certificate_value, nameplate_value, *, allow_numeric=False):
    """Describe one observed substitution without correcting either value.

    Numeric substitutions need an explicit caller opt-in after independent
    certificate/nameplate specification checks. The default remains the
    existing letter-only review comparison.
    """
    certificate, nameplate = norm(certificate_value), norm(nameplate_value)
    if (not heat_valid(certificate) or not heat_valid(nameplate) or
            len(certificate) != len(nameplate)):
        return None
    differences = [dict(position=index + 1, certificate_character=left,
                        nameplate_character=right)
                   for index, (left, right) in enumerate(zip(certificate, nameplate)) if left != right]
    if len(differences) != 1:
        return None
    # Different digits can identify different lots. They are described only
    # when the caller has supplied the stronger specification constraint;
    # missing separators and letter/digit substitutions stay excluded.
    left, right = differences[0]['certificate_character'], differences[0]['nameplate_character']
    letter = left.isascii() and left.isalpha() and right.isascii() and right.isalpha()
    digit = left.isascii() and left.isdigit() and right.isascii() and right.isdigit()
    if not (letter or (allow_numeric and digit)):
        return None
    item = differences[0]
    return dict(certificate_value=str(certificate_value), nameplate_value=str(nameplate_value),
                certificate_normalized=certificate, nameplate_normalized=nameplate,
                differences=differences, difference_type='letter' if letter else 'digit',
                description=(f'第{item["position"]}个字符'
                    f'「{item["certificate_character"]}/{item["nameplate_character"]}」不同'),
                review_only=True, write_allowed=False)
