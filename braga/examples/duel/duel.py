import re
import string
from collections import defaultdict

import six

from braga import Assemblage, Component, System, Aspect


#################################################
# Define components for players, rooms, and wand
#################################################
class Name(Component):
    """A name for the Entity. For players and wands."""

    __slots__ = ['name']

    def __init__(self, name=None):
        self.name = name


class Description(Component):
    """A description of the Entity. For all entities."""

    __slots__ = ['description']

    def __init__(self, description=None):
        self.description = description

    def get_tags(self):
        full_path_tags = set([tag for text, tag, spec, conv in string.Formatter().parse(self.description) if tag is not None])
        return set([re.match("\w+", tag) for tag in full_path_tags])


class Container(Component):
    """Ability to have an inventory. For rooms and players."""

    __slots__ = ['inventory']

    def __init__(self, inventory=None):
        self.inventory = inventory if inventory else set()


class EquipmentBearing(Component):
    """Can use Equipment. For players."""
    pass


class Mappable(Component):
    """ Ability to be part of a map, stores links to other objects on map.
        For rooms only.
    """

    __slots__ = ['paths']

    def __init__(self, paths=None):
        self.paths = paths if paths else dict()


class Moveable(Component):
    """Ability to be moved, stores Entity's location. For players and wands."""

    __slots__ = ['location']

    def __init__(self, location=None):
        self.location = location


class Equipment(Component):
    """Ability to be equipped. Stores what type of equipment the Entity is. For wands."""

    __slots__ = ['equipment_type', 'bearer']

    def __init__(self, equipment_type, bearer=None):
        self.equipment_type = equipment_type
        self.bearer = bearer


class Loyalty(Component):
    """Tracks what other Entity this Entity is loyal / belongs to. For wands."""

    __slots__ = ['owner']

    def __init__(self, owner=None):
        self.owner = owner


class ExpelliarmusSkill(Component):
    """Ability to cast expelliarmus, stores skill at casting expelliarmus. For players."""

    __slots__ = ['skill']

    def __init__(self):
        self.skill = 0


#####################################
# Define systems to manage components
#####################################

container_system = System()
equipment_system = System()


@container_system
def move(thing, new_container):
    if not thing.has_component(Moveable):
        raise ValueError("You cannot move this item")
    if not new_container.has_component(Container):
        raise ValueError("Invalid destination")
    old_container = thing.location
    thing.location = new_container
    if old_container:
        old_container.inventory.remove(thing)
    new_container.inventory.add(thing)


@equipment_system
def equip(bearer, item):
    """Equip an Entity with another Entity"""
    if not bearer.has_component(EquipmentBearing):
        raise ValueError("That cannot equip other items")
    if not item.has_component(Equipment):
        raise ValueError("That item cannot be equipped")

    try:
        equipped_item = getattr(bearer, item.equipment_type)
    except AttributeError:
        equipped_item = None

    if equipped_item:
        if equipped_item is item:
            raise ValueError("You are already equipping that item")
        else:
            raise ValueError("You are already equipping an item of this type")

    setattr(bearer, item.equipment_type, item)
    item.bearer = bearer


@equipment_system
def unequip(bearer, item):
    """Unequip an Entity from the Entity equipping it."""
    delattr(bearer, item.equipment_type)
    item.bearer = None


class NameSystem(System):
    """Associates strings with Entities."""
    def __init__(self, world):
        super(NameSystem, self).__init__(world=world, aspect=Aspect(all_of=set([Name])))
        self.names = defaultdict(lambda: None)
        self.update()

    def get_entity_from_name(self, name):
        return self.names.get(name)

    def add_alias(self, alias, entity):
        if alias in six.iterkeys(self.names):
            raise ValueError("Duplicate entity names")
        self.names[alias] = entity

    def update(self):
        for entity in self.entities:
            self.names[entity.name] = entity


class DescriptionSystem(System):
    """Updates descriptions for Entities."""
    def __init__(self, world):
        super(DescriptionSystem, self).__init__(world=world, aspect=Aspect(all_of=set([Description])))
        self.description_values = defaultdict(lambda: dict)
        self.update()

    def populate_tag_for_entity(self, tag, entity):
        if tag == 'self':
            value = entity

        value = self.world.systems[NameSystem].get_entity_from_name(tag)
        self.description_values[entity][tag] = value

    def populate_tags_for_entity(self, entity):
        if not self.description_values[entity][tag]:
            self.populate_tag_for_entity(self, tag, entity)

    def update(self):
        for entity in self.entities:
            self.populate_tags_for_entity(entity)


#########################
# Define what a player is
#########################

player_factory = Assemblage(components=[Name, Description, Container, Moveable, EquipmentBearing, ExpelliarmusSkill])

########################
# Define what a room is
########################

room_factory = Assemblage(components=[Description, Container, Mappable, Name])

#######################
# Define what a wand is
#######################

wand_factory = Assemblage(components=[Name, Description, Equipment, Moveable, Loyalty], equipment_type='wand')
