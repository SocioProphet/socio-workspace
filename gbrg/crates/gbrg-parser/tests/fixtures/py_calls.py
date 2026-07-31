# Fixture for gbrg-parser: A calls B, B calls C, and Dog(Animal) inherits.
import os


class Animal:
    def sound(self):
        return "..."


class Dog(Animal):
    def sound(self):
        return "woof"


def a():
    b()


def b():
    c()


def c():
    return os.getpid()
