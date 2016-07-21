from enum import Enum


class PostType(Enum):
    """
    From http://meta.stackexchange.com/questions/99265/values-for-posttypeid-in-data-explorer
    """

    question = 1
    answer = 2
    wiki = 3
    tag_wiki_excerpt = 4
    tag_wiki = 5
    moderator_nomination = 6
    wiki_placeholder = 7
    privilege_wiki = 8
