from ._bond_types import BondType
from ._errors import ValueOutOfRangeError


class BondValue:
    """
    Representation of any piece of data in a Bond file.
    """

    id: int = 0
    "The unique identifier of the BondValue inside its struct."
    type: BondType = BondType.Unavailable
    "The type of the BondValue."
    value: (
        int
        | str
        | float
        | bool
        | list["BondValue"]
        | dict["BondValue", "BondValue"]
        | None
    ) = None
    "The prased value of the BondValue."

    def __init__(
        self,
        id: int,
        type: BondType,
        value: int
        | str
        | float
        | bool
        | list["BondValue"]
        | dict["BondValue", "BondValue"]
        | None,
    ) -> None:
        self.id = id
        self.type = type
        self.value = value

    def get_elements(self) -> list["BondValue"]:
        """
        Returns a list of elements contained within the BondValue.
        Only applicable for List, Set, and Struct types, otherwise returns an empty list.

        Returns:
            - A list of elements contained within the BondValue.
        """
        if (
            self.type == BondType.List
            or self.type == BondType.Set
            or self.type == BondType.Struct
        ):
            if type(self.value) is list:
                return self.value
        return []

    def get_by_id(self, id: int) -> "BondValue | None":
        """
        Returns the BondValue with the specified ID within the BondValue.
        Only applicable for List, Set, and Struct types, otherwise returns None.

        Args:
            - id: The ID of the BondValue to retrieve.

        Returns:
            - The BondValue with the specified ID, or None if not found.
        """
        elements = self.get_elements()
        for element in elements:
            if element.id == id:
                return element
        return None

    def traverse(self, *ids: int, index: int = 0) -> "BondValue":
        """
        Traverses the BondValue and its children to find the element with the specified IDs.
        Only applicable for List, Set, and Struct types, otherwise returns the current BondValue.

        Args:
            - ids: The IDs of the elements to traverse.
            - index: The current index in the ID list.

        Returns:
            - The BondValue with the specified IDs, or the current BondValue if not found.
        """
        elements = self.get_elements()
        for element in elements:
            if element.id == ids[index]:
                if index == len(ids) - 1:
                    return element
                return element.traverse(index + 1, *ids)
        return self

    def get_value(self, index: int) -> "BondValue":
        """
        Returns the element at the specified index within the BondValue.
        Only applicable for List, Set, and Struct types, otherwise returns None.

        Args:
            - index: The index of the value to retrieve.

        Returns:
            - The value at the specified index.
        """
        elements = self.get_elements()
        if len(elements) > index:
            return elements[index]
        else:
            raise ValueOutOfRangeError("Index out of range for get_value")
