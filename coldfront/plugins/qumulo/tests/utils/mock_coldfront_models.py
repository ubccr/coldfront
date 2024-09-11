# This file contains a set of mock objects to reference for testing
# When trying to import these and mock these normally, pythong throws
# errors, so instead we conditionally load these in unit tests if
# we want to mock them


class Allocation:
    class objects:
        def get():
            print("bar")


class AllocationAttribute:
    class objects:
        def create():
            print("bar")


class AllocationAttributeType:
    class objects:
        def get():
            print("bar")


class Objects:
    def get():
        print("bar")
