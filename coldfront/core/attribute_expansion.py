# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# Collection of functions related to attribute expansion.
#
# This is a collection common functions related to the expansion
# of parameters (typically related to other attributes) inside of
# attributes.  Used in the expanded_value() method of AllocationAttribute
# and ResourceAttribute.

import logging
import math

logger = logging.getLogger(__name__)

# ALLOCATION_ATTRIBUTE_VIEW_LIST = import_from_settings(
#    'ALLOCATION_ATTRIBUTE_VIEW_LIST', [])

ATTRIBUTE_EXPANSION_TYPE_PREFIX = "Attribute Expanded"
ATTRIBUTE_EXPANSION_ATTRIBLIST_SUFFIX = "_attriblist"


def is_expandable_type(attribute_type):
    """Returns True if attribute_type is expandable.

    Takes an AttributeType (from either Resource or Allocation, but
    wants AttributeType, not ResourceAttributeType or
    AllocationAttributeType) and checks if type name matches
    ATTRIBUTE_EXPANSION_TYPE_PREFIX
    """

    atype_name = attribute_type.name
    return atype_name.startswith(ATTRIBUTE_EXPANSION_TYPE_PREFIX)


def get_attriblist_str(attribute_name, resources=[], allocations=[]):
    """This finds the attriblist string for the named expandable attribute.

    We append the ATTRIBUTE_EXPANSION_ATTRIBLIST_SUFFIX to the given
    attribute_name, and then search for attributes with that name in
    all resources and allocations given.  The values of any such attriblist
    attributes found are concatenated together and returned.  If no
    attriblist attributes are found, we return None.
    """

    attriblist_name = "{aname}{suffix}".format(aname=attribute_name, suffix=ATTRIBUTE_EXPANSION_ATTRIBLIST_SUFFIX)
    attriblist = None

    # Check resources first
    for res in resources:
        alist_list = res.get_attribute_list(attriblist_name)
        for alist in alist_list:
            if attriblist:
                attriblist = attriblist + "\n" + alist
            else:
                attriblist = alist
    # Then check allocations
    for alloc in allocations:
        alist_list = alloc.get_attribute_list(attriblist_name)
        for alist in alist_list:
            if attriblist:
                attriblist = attriblist + "\n" + alist
            else:
                attriblist = alist

    return attriblist


def get_attribute_parameter_value(argument, attribute_parameter_dict, error_text, resources=[], allocations=[]):
    """Evaluates the argument for a attribute parameter statement.

    This is called by process_attribute_parameter_string and handles
    evaluating/dereferencing the argument portion of the statement.

    The following argument types are recognized:
    APDICT:pname - expands to the value of a parameter named pname already
        in the attribute_parameter_dict (or None if not present)
    RESOURCE:aname - expands to the value of the first attribute of type
        named aname found in the resources list of resources.
        NOTE: 'RESOURCE:' is a literal.  Or None if not found.
    ALLOCATION:aname - expands to the value of the first attribute of type
        named aname found in the allocations list of allocations.
        NOTE: 'ALLOCATION:' is a literal.  Or None if not found.
    :keyname - expands to value of the parameter named keyname in
        attribute_parameter_dict, or if not found then will expand to the
        value of the first attribute of type named aname found in the
        allocations list, or then resources list.  Or None if all the
        preceding fail.
    'single line of text' - expands to a string literal contained between
        the two single quotes.  Very simplistic, nothing is allowed after
        the last single quote, and we just remove the leading and trailing
        single quote --- everything in between is treated literally
        (including any contained single quotes).
    digits (optionally with decimal): expands to a numeric literal

    error_text is used to give context in diagnostic messages.

    This method returns the expanded value, or None if unable to
    evaluate
    """
    value = None

    # Check for string constant
    if argument.startswith("'"):
        # Looks like a string literal
        # Strip leading quote
        tmpstr = argument[1:]
        # Verify the last character is a single quote
        tmp = tmpstr[-1:]
        if tmp == "'":
            # Good string literal
            tmpstr = tmpstr[:-1]
            return tmpstr
        else:
            # Bad string literal
            logger.warning(
                "Bad string literal '{}' found while processing {}; missing final single quote".format(
                    argument, error_text
                )
            )
            return None

    # If argument if prefixed with any of the strings in attrib_sources,
    # strip the prefix and set attrib_source accordingly
    attrib_source = None
    attrib_sources = [":APDICT", "RESOURCE:", "ALLOCATION:", ":"]
    for asrc in attrib_sources:
        if argument.startswith(asrc):
            # Got a match
            attrib_source = asrc
            tmplen = len(asrc)
            argument = argument[tmplen:]
            break

    # Try expanding as a parameter/attribute
    # We do attribute_parameter_dict first, then allocations, then
    # resources to try to get value most specific to use case
    if attribute_parameter_dict is not None and (attrib_source == ":" or attrib_source == "APDICT:"):
        if argument in attribute_parameter_dict:
            return attribute_parameter_dict[argument]

    if attrib_source == ":" or attrib_source == "ALLOCATION:":
        for alloc in allocations:
            tmp = alloc.get_attribute(argument)
            if tmp is not None:
                return tmp

    if attrib_source == ":" or attrib_source == "RESOURCE:":
        for res in resources:
            tmp = res.get_attribute(argument)
            if tmp is not None:
                return tmp

    if attrib_source is not None:
        # We were given an attribute or parameter name, but could not
        # find it.  Just return None
        return None

    # If reach here, argument is not a string literal, or a
    # parameter or attribute name, so try numeric constant
    try:
        value = int(argument)
        return value
    except ValueError:
        try:
            value = float(argument)
            return value
        except ValueError:
            logger.warning(
                "Unable to evaluate argument '{arg}' while processing {etxt}, returning None".format(
                    arg=argument, etxt=error_text
                )
            )
            return None

    # Should not reach here
    return None


def process_attribute_parameter_operation(opcode, oldvalue, argument, error_text):
    """Process the specified operation for attribute_parameter_dict.

    This is called by process_attribute_parameter_string and handles
    performing the specifed operation on the parameter.  Oldvalue is
    the starting value of the parameter (or None if not previously
    defined), opcode is the one character operation to perform, and
    argument is argument to the operation (typically the value of
    a constant, parameter, or attribute --- this should have been
    previously dereferenced by get_attribute_parameter_value).

    Opcode is the single character preceding the '=' in the parameter
    definition/statement.  E.g. the ':' in ':=', etc.  Recognized
    values are:
    : - assignment.  Any previous value of parameter will be replaced
        by argument. (Oldvalue is allowed to be None)
    | - default. If oldvalue is None, the value of the parameter is
        replaced by argument.  Otherwise, no action is taken.
    + - addition.  The new value of parameter is the oldvalue plus
        argument for numerical values.  For string values, it is
        oldvalue with argument concatenated to it (ie string +).
    - - subtraction: Numeric values only.  newval = oldvalue - argument
    * - multiplication: Numeric values only.  newval = oldvalue * argument
    / - division: Numeric values only.  newval = oldvalue / argument
    ( - apply unary function: In this case, argument is the name of an
        unary function to apply to oldvalue.  Recognized function names are:
        'floor': converts oldvalue to integer using floor()

    Error_text is used to provide context in diagnostic messages.

    On success, returns the new value that should be used for the
    parameter.  Generally returns None on errors (e.g. undefined
    required values, or bad types, etc)
    """
    # Argument should never be None
    if argument is None:
        logger.warning("Operator {}= acting on None argument in {}, returning None".format(opcode, error_text))
        return None
    # Assignment and default operations allow oldvalue to be None
    if oldvalue is None:
        if opcode != ":" and opcode != "|":
            logger.warning("Operator {}= acting on oldvalue=None in {}, returning None".format(opcode, error_text))
            return None

    try:
        if opcode == ":":
            # Assignment operation
            return argument
        if opcode == "|":
            # Defaulting operation
            if oldvalue is None:
                return argument
            else:
                return oldvalue
        if opcode == "+":
            # Addition/concatenation operation
            if isinstance(oldvalue, int) or isinstance(oldvalue, float):
                newval = oldvalue + argument
                return newval
            elif isinstance(oldvalue, str):
                newval = oldvalue + argument
                return newval
            else:
                logger.warning(
                    "Operator {}= acting on parameter of type {} in {}, returning None".format(
                        opcode, type(oldvalue), error_text
                    )
                )
                return None
        if opcode == "-":
            newval = oldvalue - argument
            return newval
        if opcode == "*":
            newval = oldvalue * argument
            return newval
        if opcode == "/":
            newval = oldvalue / argument
            return newval
        if opcode == "(":
            if argument == "floor":
                newval = math.floor(oldvalue)
            else:
                logger.error(
                    "Unrecognized function named {} in {}= for {}, returning None".format(argument, opcode, error_text)
                )
                return None
        # If reached here, we do not recognize opcode
        logger.error("Unrecognized operation {}= in {}, returning None".format(opcode, error_text))
    except Exception:
        logger.warning(
            "Error performing operator {op}= on oldvalue='{old}' and argument={arg} in {errtext}".format(
                op=opcode, old=oldvalue, arg=argument, errtext=error_text
            )
        )
        return None


def process_attribute_parameter_string(
    parameter_string, attribute_name, attribute_parameter_dict={}, resources=[], allocations=[]
):
    """Processes a single attribute parameter definition/statement.

    This is called by make_attribute_parameter_dictionary, and handles
    the processing of a single attribute parameter definition/statement
    given by 'parameter_string' in the attribute parameter list.  The
    passed attribute_parameter_dict, as well as passed lists of resources
    and allocations, will be used when dereferencing parameters/attributes,
    and the new value for any parameter will be stored back in the
    attribute_parameter_dict, which is also returned.

    Attribute_name is just used in diagnostic messages.

    Each statement should have the general form:
    '<parameter_name> <op>= <argument>'
    <parameter_name> is the name of the parameter in
    attribute_parameter_dict to create/update.
    <op> is a single character operator defining the operation to do
    on the specified parameter.
    <argument> is an additional argument to use in the operation.  Typically
    it will be a numeric constant, a string constant, or the name of an
    AllocationAttribute or ResourceAttribute (which is then replaced by
    its (expanded if expandable) value).

    See the methods get_attribute_parameter_value() and
    process_attribute_parameter_operation() for more information about
    the operations and argument values.
    """

    # Strip leading/trailing white space
    parmstr = parameter_string.strip()
    # Ignore comment lines/blank lines (return attribute_parameter_dict)
    if not parmstr:
        return attribute_parameter_dict
    if parmstr.startswith("#"):
        return attribute_parameter_dict

    # Parse the parameter string to get pname, op, and argument
    tmp = parmstr.split("=", 1)
    if len(tmp) != 2:
        # No '=' found, so invalid format of parmstr
        # Log error and return unmodified attribute_parameter_dict
        logger.error(
            "Invalid parameter string '{pstr}', no '=', while "
            "creating attribute parameter dictionary for expanding "
            "attribute {aname}".format(aname=attribute_name, pstr=parameter_string)
        )
        return attribute_parameter_dict
    pname = tmp[0]
    argument = tmp[1].strip()
    # Remove opcode and remove trailing whitespace from pname
    opcode = pname[-1:]
    pname = pname[:-1].strip()

    # Argument is a parameter/attribute/constant unless opcode is '('
    # So get its value if parameter/attribute/constant
    value = None
    if opcode == "(":
        value = argument
    else:
        # Extra text to display in diagnostics if error occurs
        error_text = "processing attribute_parameter_string={pstr} for expansion of attribute {aname}".format(
            pstr=parameter_string, aname=attribute_name
        )
        value = get_attribute_parameter_value(
            argument=argument,
            attribute_parameter_dict=attribute_parameter_dict,
            resources=resources,
            allocations=allocations,
            error_text=error_text,
        )

    # Get the old value of the parameter
    if pname in attribute_parameter_dict:
        oldval = attribute_parameter_dict[pname]
    else:
        oldval = None

    # Perform the requested operation
    newval = process_attribute_parameter_operation(
        opcode=opcode, oldvalue=oldval, argument=value, error_text=error_text
    )
    # Set value in dictionary and return
    attribute_parameter_dict[pname] = newval
    return attribute_parameter_dict


def make_attribute_parameter_dictionary(attribute_name, attribute_parameter_string, resources=[], allocations=[]):
    """Create the attribute parameter dictionary.  Used by expand_attribute.

    This processes the given attribute parameter string to generate a
    dictionary that will (in expand_attribute()) be passed as the argument
    to the standard python format() method acting on the raw value of the
    attribute to expand it.

    The attribute parameter string is a string consisting of one or more
    attribute parameter definitions, one per line, with the following
    general format:
    '<parameter_name> <op>= <argument>'

    This routine processes the attribute_parameter_string line by line, in
    order top to bottom, to generate the dictionary that is returned.

    See process_attribute_parameter_string for details on the processing
    of each line.
    """

    # Initialize our dictionary
    apdict = dict()

    # Covert attribute_parameter_string to a real list
    attrib_parm_list = list(map(str.strip, attribute_parameter_string.splitlines()))
    # Process each element in the list
    for parmstr in attrib_parm_list:
        apdict = process_attribute_parameter_string(
            parameter_string=parmstr,
            attribute_parameter_dict=apdict,
            attribute_name=attribute_name,
            resources=resources,
            allocations=allocations,
        )
    return apdict


def expand_attribute(raw_value, attribute_name, attriblist_string, resources=[], allocations=[]):
    """Main method to expand parameters in an attribute.

    This takes the (raw) value raw_value of either an AllocationAttribute
    or ResourceAttribute, which should be in a python formatted string
    (f-string) format; i.e. a string with places where parameter
    replacement is desired to have the name of the desired replacement
    parameter enclosed in curly braces ('{' and '}').  The parameter name
    can be followed by standard format() format specifiers, as per
    standard format() rules.  The argument attribute_name should have
    the name of this attribute, for use in diagnostic messages.

    The parameters and their values are defined in attriblist_string.
    This string consists of one or more parameter declaration statements,
    one per line.  Each parameter declaration statement is of the form
    '<parameter_name> <op>= <argument>'
    Leading and trailing whitespace, as well as whitespace around the
    <op>= string, is ignored.
    These statements are processed in order from top to bottom.

    <parameter_name> is the name of the parameter to be defined/operated
    on, and should be a valid python identifier.  You can give the same
    <parameter_name> on multiple lines to perform multiple operations on
    the parameter, e.g. set it from an attribute then multiple by another
    attribute.

    <op> is a single character defining the operation to perform; see
    the process_attribute_parameter_operation method for list of allowed
    operations.

    <argument> is an argument for use in the operation.  Typically it is
    a string or numeric constant, or the name an Attribute in either
    one of the listed resources or allocations (which would then be looked
    up and the value returned).  See the get_attribute_parameter_value()
    method for more information.

    This method will parse the attriblist_string to form an attribute
    parameter dictionary, which will then be used via the standard python
    format() method to expand the parameters in the raw_value.  If all
    of this is successful, we return the expanded string.

    On errors, we just return the raw_value
    """

    # We wrap everything in a try block so we can return raw_value on error
    try:
        # Create the attribute parameter dictionary
        apdict = make_attribute_parameter_dictionary(
            attribute_parameter_string=attriblist_string,
            attribute_name=attribute_name,
            resources=resources,
            allocations=allocations,
        )

        # Expand the attribute
        expanded = raw_value.format(**apdict)
        return expanded
    except Exception as xcept:
        # We got an exception.  This could be for many reasons, from
        # referencing a parameter not defined in apdict to divide by
        # zero errors in processing apdict.  We just log it and then
        # return raw_value
        logger.error("Error expanding {aname}: {error}".format(aname=attribute_name, error=xcept))
        return raw_value


def convert_type(value, type_name, error_text="unknown"):
    """This returns value with a python type corresponding to type_name.

    Value is the value to operate on.
    Type_name is the name of the underlying attribute type (AttributeType),
    e.g. Text, Float, Int, Date, etc.

    If type_name ends in Int, we try to return value as a python int.
    If type_name ends in Float, we try to return value as a python float.
    If type_name ends in Text, we try to return value as a python string.
    For anything else, we just return value (which typically is a string)
    If there is an error in the conversion, we just return value (and
    log the error; error_text is used in such messages to provide context)

    We compare the end of the type name, to allow for possible
    future "Attribute Expanded ..." types.
    """
    if type_name is None:
        logger.error("No AttributeType found for {}".format(error_text))
        return value

    if type_name.endswith("Text"):
        try:
            newval = str(value)
            return newval
        except ValueError:
            logger.error('Error converting "{}" to {} in {}'.format(value, "Text", error_text))
            return value

    if type_name.endswith("Int"):
        try:
            newval = int(value)
            return newval
        except ValueError:
            logger.error('Error converting "{}" to {} in {}'.format(value, "Int", error_text))
            return value

    if type_name.endswith("Float"):
        try:
            newval = float(value)
            return newval
        except ValueError:
            logger.error('Error converting "{}" to {} in {}'.format(value, "Float", error_text))
            return value

    # If not any of the above, just return the value (probably a string)
    return value
