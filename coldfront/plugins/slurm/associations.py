import datetime
import logging
import os
import re
import sys

from coldfront.core.resource.models import Resource
from coldfront.plugins.slurm.utils import (SLURM_ACCOUNT_ATTRIBUTE_NAME,
                                           SLURM_CLUSTER_ATTRIBUTE_NAME,
                                           SLURM_SPECS_ATTRIBUTE_NAME,
                                           SLURM_USER_SPECS_ATTRIBUTE_NAME,
                                           slurm_add_cluster,
                                           slurm_modify_cluster,
                                           slurm_remove_cluster,
                                           slurm_add_account,
                                           slurm_remove_account, 
                                           slurm_modify_account,
                                           slurm_add_assoc, 
                                           slurm_remove_assoc, 
                                           slurm_modify_assoc,
                                           SlurmError)

logger = logging.getLogger(__name__)

ROOT_USER_SPEC_LIST = [ 
    "DefaultAccount='root'",
    "AdminLevel='Administrator'",
    "Fairshare=1", ]
ROOT_USER_SPEC_STRING = ':'.join(ROOT_USER_SPEC_LIST)

class SlurmParserError(SlurmError):
    pass
 
class SlurmSpecParseError(SlurmError):
    pass


class SlurmBase:
    def __init__(self, name, specs=None):
        if specs is None:
            specs = []

        self.name = name
        self.specs = specs

    def spec_list(self, specs=None):
        """Return unique list of Slurm Specs

        Takes a list of strings. Each string can have a single
        spec reference (key=value), or multiple separated by 
        colons (:)

        specs defaults to self.specs
        """
        if specs is None:
            specs = self.specs
        if specs is None:
            specs = []
        items = []
        for s in specs:
            for i in s.split(':'):
                items.append(i)

        # Remove duplicates
        items = list(set(items))
        # Sort results (this is only to make consistent ordering for
        # unit tests.  Small overhead as usually small lists)
        #items.sort()
        return items

    def format_specs(self, specs=None):
        """Format unique list of Slurm Specs

        Takes a list of strings specs.
        Specs defaults to self.specs
        """
        if specs is None:
            specs = self.specs
        if specs is None:
            return ''
        slist = self.spec_list(specs=specs)
        # Sort results (this is only to make consistent ordering for
        # unit tests.  Small overhead as usually small lists)
        slist.sort()
        #return ':'.join([x for x in self.spec_list(specs=specs)])
        return ':'.join([x for x in slist])

    def _write(self, out, data):
        try:
            out.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def strip_spec_value(self, value):
        """Removes single or double quote from a spec value.
        
        Also removes leading/trailing whitespace (outside of any
        quotes).  Returns stripped value.
        """
        new = value.strip()
        if ( (new.startswith('"') and new.endswith('"')) or
            (new.startswith("'") and new.endswith("'"))):
            # new begins and ends with either ' or " (but same on each end)
            new = new[1:-1]
        return new
            
    def spec_dict(self, specs=None):
        """Return dictionary representation of specs.

        specs should be a list of strings.
        If specs is not given, defaults to self.specs
        Splits spec string on colon, and then each record split
        at the first equal sign into a field name and value. (We
        handle the += and -= specially, as described below.)

        The dictionary wil be keyed on the the (lowercased) field
        name.  The value will represent the value; for most attributes
        the dictionary value is simply the value of the attribute.

        For set style attributes, which accept =, +=, and == operators
        (e.g. QOS), the +/- symbol is stripped from the fieldname.
        The dictionary value will be the result of splitting the value string
        on commas, prepending a '+' or '-' to each element for operators
        '+=' or '-=', respectively (for '=', nothing is prepended), and
        storing as a set.

        For TRES based attributes, the value portion of the string is a 
        comma delimitted set of field=val; this is represented as a dictionary
        value, keyed on field.

        If key is duplicated, for simple values the last entry wins.  For
        others, the values are merged, as follows:

        For TRES based values, the dicts are merged, key by key.  Keys in
        new dict are added to the old dict, clobbering old values if the
        key is in the old dict as well.  Keys in the old dict not present
        in the new dict will be kept.

        For QOS and similar sets based, the sets are merged.  For every
        element in the new set, we look at the base element (with leading
        '+' or '-' stripped), and if that base element, or the base element
        with either '+' or '-' prefix exists in old, it is removed.  Then
        the new element (with any prefix it has) is added.

        NOTE: some testing with Slurm 20.11 and QoS field suggests that it
        is *not advisible* to mix = and either += or -= operators on the same
        field, even when the operators are acting on different qoses.  E.g.,
        creating an account with qos=foo +qos=bar results in an account with
        qoses 'foo,+bar' (note invalid +bar qos).  If the qos= argument comes
        after a qos-= or qos+=, the qos= argument will act as qos+= or qos-=,
        mimicing whichever came just before it. Mixing just qos+=foo and 
        qos-=foo seems to be more consistent, with whichever was given last
        having effect.  This situation appears to be an issue in Slurm, and
        beyond the purview of coldfront; the approach we are using seems
        reasonable in view of this.  It is advised to avoid mixing the three
        operators (=, +=, and -=) for the same field, and strongly advised to
        avoid mixing = with either of the others --- if you do so, use extreme
        care.
        """
        parsed = {}
        if specs is None:
            specs = self.specs
        if not specs:
            # No specs, return an empty dictionary
            return parsed
        records = self.spec_list(specs=specs)

        # Fields that have "set" semantics (e.g. take =, +=, -=)
        slurm_spec_set_fields = { 'qos' }

        for record in records:
            if record == '':
                continue
            # Split the record on the (first) =/+=/-= operator
            # Operator stored in op
            (field, value) = record.split('=', maxsplit=1)
            key = field.strip().lower()
            value = self.strip_spec_value(value)
            op = '='
            if key[-1] == '+':
                op = '+='
                key = key[0:-1]
            elif key[-1] == '-':
                op = '-='
                key = key[0:-1]

            # Handle special fields

            #   Set values accepting =/+=/-=
            if key in slurm_spec_set_fields:
                vals = value.split(',')
                vals = list(map(str.strip, vals))
                if op == '+=':
                    vals = list(map(lambda x: '+{}'.format(x), vals))
                elif op == '-=':
                    vals = list(map(lambda x: '-{}'.format(x), vals))

                # Merge with previous
                if key in parsed:
                    oldvalset = parsed[key]
                    for newval in vals:
                        basenewval = newval
                        if (newval.startswith('+') 
                            or newval.startswith('-') ):
                                basenewval=newval[1:0]
                        # Remove basenewval, +basenewval, -basenewval
                        oldvalset.discard(basenewval)
                        oldvalset.discard('+{}'.format(basenewval))
                        oldvalset.discard('-{}'.format(basenewval))
                        oldvalset.add(newval)
                    vals = oldvalset
                else:
                    vals = set(vals)

                parsed[key] = vals
                continue

            if op != '=':
                raise SlurmSpecParseError('Encountered op {} for non-list '
                    'field={}'.format(op, field))

            #   TRES values
            if 'tres' in key:
                # Got a TRES field, split on commans
                tresrecs = value.split(',')
                tresrecs = map(str.strip, tresrecs)
                tresdict = {}
                for tresrec in tresrecs:
                    (tresfld, tresval) = tresrec.split('=', maxsplit=1)
                    tresfld = tresfld.strip().lower()
                    tresval.strip()

                    if tresfld in tresdict:
                        raise SlurmSpecParseError('Encountered duplicate TRES '
                            '{} in Slurm attribute {}: first={}, second={}'.format(
                            tresfld, field, tresdict[tresfld], tresval))
                    tresdict[tresfld] = tresval

                # Merge with previous
                if key in parsed:
                    olddict = parsed[key]
                    for newkey, newval in tresdict.items():
                        olddict[newkey] = newval
                    tresdict = olddict

                parsed[key] = tresdict
                continue

            # Simple case
            parsed[key] = value

        return parsed

    def compare_slurm_specs(self, spec2, flags=[], spec1=None):
        """Compare two parsed Slurm specs.

        spec1 and spec2 should be dictionary representations of the 
        specs to compare (e.g. as from  spec_dict)
        If spec1 is omitted, it defaults to self.spec_dict()

        If the specs are the same (after ignore flags taken into account)
        returns false.  

        If the specs disagree (after ignore flags), then returns a list
        of strings of format '<specfield>=<value>' which will convert
        entity with spec1 into entity with spec2.  This will change spec
        fields which differ between the two, add spec fields present in
        spec2 only, and 'delete' fields in spec1 only.  Fields (and/or
        subvalues of fields) that are 'ignored' will remain unchanged.
        """
        if spec1 is None:
            spec1 = self.spec_dict()

        # Get the flags with 'ignore_' prefix.  Keep ignore_order* flags
        # separate.  And strip 'ignore_' prefix for normal ignore_flags
        ignore_flags = list(filter(lambda x: x.startswith('ignore_'), 
            flags))
        ignore_fields = list(map(lambda x: x.replace('ignore_',''), 
            ignore_flags))

        # Convert to sets, and delete any ignored keys
        set1 = set(spec1.keys())
        set2 = set(spec2.keys())
        for ignore in ignore_fields:
            set1.discard(ignore)
            set2.discard(ignore)
        #sys.stderr.write('[TPTEST] STarting compare_slurm_specs\n')
        #sys.stderr.write('[TPTEST] spec1="{}"\n'.format(spec1))
        #sys.stderr.write('[TPTEST] spec2="{}"\n'.format(spec2))
        #sys.stderr.write('[TPTEST] set1="{}"\n'.format(set1))
        #sys.stderr.write('[TPTEST] set2="{}"\n'.format(set2))
        #sys.stderr.write('[TPTEST] ignore_flags="{}"\n'.format(ignore_flags))

        # Get keys only in spec1, only in spec2, and in both
        spec1only = set1 - set2
        spec2only = set2 - set1
        spec1and2 = set2.intersection(set1)

        # Slice the spec dictionaries for toadd
        toadd = { key:spec2[key] for key in spec2only }

        # For todel, we need to set values of todel hash
        # to delete the value
        todel = {}
        nullable_fields = { 'description', 'org', }
        # Set arguments to delete options set only in spec1
        for key in spec1only:
            oldvalue = spec1[key]
            if key == 'parent':
                # To 'delete' parent setting, set to 'root'
                todel['parent'] = 'root'
            elif key in nullable_fields:
                todel[key] = None
            elif type(oldvalue) == dict:
                tmp = {}
                for skey in oldvalue.keys():
                    tmp[skey] = -1
                todel[key] = tmp
            elif type(oldvalue) == set:
                # Handle qos and other(?) set type values
                # Based on tests with Slurm 20.11, to remove qos
                # specifications from an existing association and
                # restore the defaults, we should set qos=
                todel[key] = None
            else:
                # All other fields seem to want to be set to -1 
                # in sacctmgr in order to remove the setting
                todel[key] = -1

        # To mod is more complicated, need to actually compare values
        tomod = {}
        for key in spec1and2:
            rawval1 = spec1[key]
            rawval2 = spec2[key]
            val1 = rawval1
            val2 = rawval2

            # Handle special ignored flags if key is a TRES type
            if 'tres' in key:
                # Don't modify original specs
                val1 = dict(rawval1)
                val2 = dict(rawval2)

                # Find all ignore_fields of form <key>_, and strip prefix
                # (if ignore_key was present, we don't even reach here)
                prefix = '{}_'.format(key)
                ignore_subfields = list(filter(
                    lambda x: x.startswith(prefix), ignore_fields))
                ignore_subfields = list(map(
                    lambda x: x.replace(prefix,''), ignore_subfields))
                for ignore_subfield in ignore_subfields:
                    val1.pop(ignore_subfield, None)
                    val2.pop(ignore_subfield, None)

                # For TRES fields, we only want fields which differ
                tmp = list(val1.keys())
                for subkey in tmp:
                    if subkey in val2:
                        if val1[subkey] == val2[subkey]:
                            # Delete identical subkeys
                            val1.pop(subkey, None)
                            val2.pop(subkey, None)

            if val1 == val2:
                continue

            if type(val1) == dict:
                # If there are any TRES fields in val1 but not in val2, we
                # need to add field to val2 with value -1 to disable
                tmp1 = set(val1.keys())
                tmp2 = set(val2.keys())
                tmp1only = tmp1 - tmp2
                for skey in tmp1only:
                    # Sacctmgr wants TRES set to -1 to disable previous setting
                    val2[skey] = -1

            if type(val1) == set:
                # Try to handle qos and other set-like attributes
                # If val2 is only absolute, we are done.
                # If val2 has += or -=, then for any items in old which had
                # = or += as operation will be added to negative list for val2
                # unless it shows up in += or = lists for val2
                newvlist = list(val2)
                newnlist = list(filter(lambda x: 
                    not ( x.startswith('+') or x.startswith('-')), newvlist))
                newolist = list(filter(lambda x: 
                     x.startswith('+') or x.startswith('-'), newvlist))
                newolist = list(map(lambda x: x[1:], newolist))
                newbasenames = set(newolist+newnlist)

                oldvlist = list(val1)
                oldplist = list(filter(lambda x: x.startswith('+'), oldvlist))
                oldplist = list(map(lambda x: x[1:], oldplist))
                oldnlist = list(filter(lambda x: 
                    not ( x.startswith('+') or x.startswith('-')), oldvlist))
                oldnplist = oldplist + oldnlist
                for oldbase in oldnplist:
                    if oldbase not in newbasenames:
                        val2.add('-{}'.format(oldbase))

            # Values differ, add to to mod
            tomod[key] = val2

        # Now convert toadd, todel, tomod to a list of spec strings to set
        # Mostly done by spec_dict_to_list()
        specs_list = []
        tmp = self.spec_dict_to_list(todel)
        if tmp:
            specs_list.extend(tmp)
        tmp = self.spec_dict_to_list(toadd)
        if tmp:
            specs_list.extend(tmp)
        tmp = self.spec_dict_to_list(tomod)
        if tmp:
            specs_list.extend(tmp)

        if specs_list:
            return specs_list
        return False
 
    def spec_dict_to_list(self, spec_dict=None):
        """Converts a spec_dict to list format.

        Takes a spec_dict and converts to list of field=value strings.
        spec_dict defaults to self.spec_dict()
        """
        if spec_dict is None:
            spec_dict = self.spec_dict()

        spec_list = []
        for key, value in spec_dict.items():
            if value is None:
                # These should be represented by key= with nothing
                # on RHS of =
                spec_str = '{}='.format(key)
                spec_list.append(spec_str)
                continue
            if type(value) == set:
                # Handle qos and other(?) set type values
                # This is tricky, due to ability to use =, += and -=
                # operators, especially since Slurm does not seem to
                # handle mixing of operators very well (at least based
                # on my tests with Slurm 20.11.  See note on spec_dict())
                # We add up to 3 records, first for key+=, then key=
                # then key-=.  Should work fine if only a single operator
                # given for the key; otherwise behavior is reasonable.
                # We strongly advise users not to mix operators on the
                # same field.
                vlist = list(value)
                # Separate elements starting with +, - or neither
                plist = list(filter(lambda x: x.startswith('+'), vlist))
                mlist = list(filter(lambda x: x.startswith('-'), vlist))
                nlist = list(filter(lambda x: 
                    not ( x.startswith('+') or x.startswith('-')), vlist))
                # Remove leading +/- on the respective elements
                plist = list(map(lambda x: x[1:], plist))
                mlist = list(map(lambda x: x[1:], mlist))

                if plist:
                    tmp = '{}+={}'.format(key, ','.join(plist))
                    spec_list.append(tmp)
                if nlist:
                    tmp = '{}={}'.format(key, ','.join(nlist))
                    spec_list.append(tmp)
                if mlist:
                    tmp = '{}-={}'.format(key, ','.join(mlist))
                    spec_list.append(tmp)
                continue
            elif type(value) == dict:
                # Got a dict, TRES-type field
                tmp = []
                for dkey, dval in value.items():
                    tmpstr = '{}={}'.format(dkey, dval)
                    tmp.append(tmpstr)
                spec_str = '{}={}'.format(key, ','.join(tmp))
                spec_list.append(spec_str)
                continue
            else:
                # Simple field
                spec_str = '{}={}'.format(key, value)
                spec_list.append(spec_str)
                continue

        return spec_list


class SlurmUser(SlurmBase):
    @classmethod
    def new_from_sacctmgr(SlurmUser_class, line):
        """Create a new SlurmUser by parsing a line from sacctmgr dump. For
        example: User - 'jane':DefaultAccount='physics':Fairshare=Parent:QOS='general-compute'"""
        if not re.match("^User - '[^']+'", line):
            raise(SlurmParserError(
                'Invalid format. Must start with "User" for line: {}'.format(line)))

        parts = line.split(':')
        name = re.sub(r"^User - ", '', parts[0]).strip("\n'")
        if len(name) == 0:
            raise(SlurmParserError('User name not found for line: {}'.format(line)))

        return SlurmUser_class(name, specs=parts[1:])

    def write(self, out):
        self._write(out, "User - '{}':{}\n".format(
            self.name,
            self.format_specs(),
        ))

    @classmethod
    def update_user_to(
        SlurmUser_class, old, new, flags=[], 
        noop=False, cluster=None, account=None, noout=False):
        """Issue Slurm commands to update the user old to new.

        If old == None, creates the user
        If new == None, deletes the user

        account is the name of the account containing the users, required.
        cluster is the name of the cluster containing the accounts,
        required.

        If noop is given, do not actually run commands just print them 
        (unless noout is set) and return text of commands run.

        Flags should be a list of flags controlling behavior.  Any flags
        given will be passed to update_*_to and compare_slurm_specs 
        methods of descendent users beneath the account,
        and therefore unrecognized flags are ignored.  Typically, flags
        will have an action prefix (e.g. ignore_*, skip_*, force_*),
        followed by a name or name_subname.  All flags default to
        unset.

        Flags recognized by update_user_to are:
            skip_create_user: if set, do not create user
                if missing.  If old user is missing, just return.
            skip_delete_user: if set, do not delete user
                if new is None. 
            skip_user_specs: if set, do not compare the user
                specs.
            ignore_<spec_field>: if set, compare_slurm_specs will
                ignore the value of the spec_field Slurm spec when
                comparing specs.  For list-valued/TRES-valued fields,
                the entire field is ignored.
            ignore_<spec_field>_<subfld>: if set and spec_field is
                TRES-valued, the TRES named <tag> is ignored by 
                compare_slurm_specs for that spec_field.
        """
        output = ''
        if account is None:
            raise SlurmError('Required parameter account missing')
        if cluster is None:
            raise SlurmError('Required parameter cluster missing')

        if old is None:
            # Old user does not exist, so add new user
            if new is None:
                # But neither does new, huh?  But not an error
                return
            if 'skip_create_user' in flags:
                logger.info('Not creating user {}: '
                    'skip_create_user is set'.format(new.name))
                return output

            # Add the user
            new_name = new.name
            new_specs = new.spec_dict_to_list()
            return slurm_add_assoc(
                user=new_name,
                account=account,
                cluster=cluster,
                specs=new_specs, 
                noop=noop, 
                noout=noout)
        
        # Old exists
        if new is None:
            # New user does not exist, so delete old user
            #
            if 'skip_delete_user' in flags:
                logger.info('Not deleting user {}: '
                    'skip_delete_user is set'.format(old.name))
                return output

            return slurm_remove_assoc(
                user=old.name,
                cluster=cluster,
                account=account,
                noop=noop, 
                noout=noout)

        # Both old and new exist, compare them
        diffs = False
        if not 'skip_user_specs' in flags:
            diffs = old.compare_slurm_specs(
                spec2=new.spec_dict(), flags=flags)
            #sys.stderr.write('[TPTEST] compare_slurm_specs returned {}\n'.format(diffs))


        if diffs:
            return slurm_modify_assoc(
                user=new.name, 
                cluster=cluster,
                account=account,
                specs=diffs, 
                noop=noop, 
                noout=noout)
        return output


class SlurmAccount(SlurmBase):
    SlurmUser_class = SlurmUser
    def __init__(self, name, specs=None, parent=None):
        super().__init__(name, specs=specs)
        self.users = {}
        self.parent = parent

    @classmethod
    def new_from_sacctmgr(SlurmAccount_class, line, parent=None):
        """Create a new SlurmAccount by parsing a line from sacctmgr dump. For
        example: Account - 'physics':Description='physics group':Organization='cas':Fairshare=100"""
        if not re.match("^Account - '[^']+'", line):
            raise(SlurmParserError(
                'Invalid format. Must start with "Account" for line: {}'.format(line)))

        parts = line.split(':')
        name = re.sub(r"^Account - ", '', parts[0]).strip("\n'")
        if len(name) == 0:
            raise(SlurmParserError(
                'Cluster name not found for line: {}'.format(line)))

        return SlurmAccount_class(name, specs=parts[1:], parent=parent)

    def add_allocation(self, allocation, user_specs=None):
        """Add users from a ColdFront Allocation model to SlurmAccount"""
        if user_specs is None:
            user_specs = []

        name = allocation.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = 'root'

        if name != self.name:
            raise(SlurmError('Allocation {} slurm_account_name does not match {}'.format(
                allocation, self.name)))

        self.specs += allocation.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)

        allocation_user_specs = allocation.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        for u in allocation.allocationuser_set.filter(status__name='Active'):
            user = self.SlurmUser_class(u.user.username)
            user.specs += allocation_user_specs
            user.specs += user_specs
            self.add_user(user)


    def add_user(self, user):
        if user.name not in self.users:
            self.users[user.name] = user

        rec = self.users[user.name]
        rec.specs += user.specs
        self.users[user.name] = rec

    def write(self, out):
        if self.parent is not None:
            self._write(out, "Parent - '{}'\n".format(self.parent.name))
        if self.name != 'root':
            self._write(out, "Account - '{}':{}\n".format(
                self.name,
                self.format_specs(),
            ))

    def write_users(self, out):
        self._write(out, "Parent - '{}'\n".format(self.name))
        for uid, user in self.users.items():
            user.write(out)

    @classmethod
    def update_account_to(
        SlurmAccount_class, old, new, flags=[], 
            noop=False, cluster=None, noout=False):
        """Issue Slurm commands to update the account old to new.

        If old == None, creates the account
        If new == None, deletes the account
        Will recursively go through users, etc.

        cluster is the name of the cluster containing the accounts,
        required.

        If noop is set, do not actually run commands print them
        (unless noout is set) and return text with commands would have run

        Flags should be a list of flags controlling behavior.  Any flags
        given will be passed to update_*_to and compare_slurm_specs 
        methods of descendent users beneath the account,
        and therefore unrecognized flags are ignored.  Typically, flags
        will have an action prefix (e.g. ignore_*, skip_*, force_*),
        followed by a name or name_subname.  All flags default to
        unset.

        Flags recognized by update_account_to are:
            skip_create_account: if set, do not create account
                if missing.  If old account is missing, just return.
            skip_delete_account: if set, do not delete account
                if new is None. 
            skip_account_specs: if set, do not compare the account
                specs.
            ignore_<spec_field>: if set, compare_slurm_specs will
                ignore the value of the spec_field Slurm spec when
                comparing specs.  For list-valued/TRES-valued fields,
                the entire field is ignored.
            ignore_<spec_field>_<subfld>: if set and spec_field is
                TRES-valued, the TRES named <tag> is ignored by 
                compare_slurm_specs for that spec_field.

        NOTE: skip_delete_account will also prevent the deletion of
            users underneath the account to be deleted.
        NOTE: skip_delete_user will be *ignored* for users of an
            account being deleted.
        """
        output = ''
        if cluster is None:
                raise SlurmError('Required parameter cluster missing')

        if old is None:
            # Old account does not exist, so add new account
            if new is None:
                # But neither does new, huh?  But not an error
                return output
            if 'skip_create_account' in flags:
                logger.info('Not creating account {}: '
                    'skip_create_account is set'.format(new.name))
                return output

            # Add the account
            new_name = new.name
            new_specs = new.spec_dict_to_list()
            output = slurm_add_account(
                cluster=cluster,
                account=new_name, 
                specs=new_specs, 
                parent=new.parent,
                noop=noop,
                noout=noout)

            # Add the users under the account
            for user in new.users.values():
                tmpout = user.update_user_to(
                    old=None,
                    new=user,
                    flags=flags,
                    cluster=cluster,
                    account=new_name,
                    noop=noop,
                    noout=noout)
                output += tmpout
            return output
        
        # Old exists
        if new is None:
            # New account does not exist, so delete old account
            #
            if 'skip_delete_account' in flags:
                logger.info('Not deleting account {}: '
                    'skip_delete_account is set'.format(old.name))
                return output

            output = ''
            # First delete all of our users

            # Remove skip_delete_user flag for this special case
            tmpflags = flags
            if 'skip_delete_user' in tmpflags:
                tmpflags.remove('skip_delete_user')
            
            for user in old.users.values():
                tmpout = user.update_user_to(
                    old=user,
                    new=None,
                    flags=tmpflags, 
                    cluster=cluster,
                    account=old.name,
                    noop=noop,
                    noout=noout)
                output += tmpout
            # Then delete the account
            tmpout = slurm_remove_account(
                cluster=cluster,
                account=old.name,
                noop=noop,
                noout=noout)
            output += tmpout
            return output

        # Both old and new exist, compare them
        output = ''
        diffs = False
        if not 'skip_account_specs' in flags:
            diffs = old.compare_slurm_specs(
                spec2=new.spec_dict(), flags=flags)

        # Compare parents of the account
        old_parent = 'root'
        new_parent = 'root'
        if old.parent is not None:
            old_parent = old.parent.name
        if new.parent is not None:
            new_parent = new.parent.name
        if old_parent != new_parent:
            if not diffs:
                diffs = []
            diffs.append('Parent={}'.format(new_parent))
                
        if diffs:
            tmpout = slurm_modify_account(
                account=new.name, 
                cluster=cluster,
                specs=diffs, 
                noop=noop,
                noout=noout)
            output += tmpout

        # Now compare users old vs new
        for uname, olduser in old.users.items():
            if uname in new.users:
                #User exists in both old and new
                newuser = new.users[uname]
                tmpout = olduser.update_user_to(
                    old=olduser,
                    new=newuser,
                    cluster=cluster,
                    account=new.name,
                    flags=flags,
                    noop=noop,
                    noout=noout)
                output += tmpout
            else:
                #User only exists in old
                tmpout = olduser.update_user_to(
                    old=olduser,
                    new=None,
                    cluster=cluster,
                    account=new.name,
                    flags=flags,
                    noop=noop,
                    noout=noout)
                output += tmpout
        for uname, newuser in new.users.items():
            # We only consider users in new but not old, as
            # handled others in above
            if not uname in old.users:
                tmpout = newuser.update_user_to(
                    old=None,
                    new=newuser,
                    cluster=cluster,
                    account=new.name,
                    flags=flags,
                    noop=noop,
                    noout=noout)
                output += tmpout
        
        return output

class SlurmCluster(SlurmBase):
    SlurmAccount_class = SlurmAccount
    SlurmUser_class = SlurmUser
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.accounts = {}

    @classmethod
    def new_from_stream(SlurmCluster_class, stream):
        """Create a new SlurmCluster by parsing the output from sacctmgr dump."""
        cluster = None
        parent = None
        for line in stream:
            line = line.strip()
            if re.match("^#", line):
                continue
            elif re.match("^Cluster - '[^']+'", line):
                parts = line.split(':')
                name = re.sub(r"^Cluster - ", '', parts[0]).strip("\n'")
                if len(name) == 0:
                    raise(SlurmParserError(
                        'Cluster name not found for line: {}'.format(line)))
                cluster = SlurmCluster_class(name)
                cluster.specs += parts[1:]
            elif re.match("^Account - '[^']+'", line):
                parent_account = None
                if parent:
                    parent_account = cluster.accounts[parent]
                account = SlurmCluster_class.SlurmAccount_class.new_from_sacctmgr(
                    line, parent=parent_account)
                cluster.accounts[account.name] = account
            elif re.match("^Parent - '[^']+'", line):
                parent = re.sub(r"^Parent - ", '', line).strip("\n'")
                if parent == 'root':
                    if 'root' not in cluster.accounts:
                        cluster.accounts['root'] = \
                            SlurmCluster_class.SlurmAccount_class('root')
                if not parent:
                    raise(SlurmParserError(
                        'Parent name not found for line: {}'.format(line)))
            elif re.match("^User - '[^']+'", line):
                user = SlurmCluster_class.SlurmUser_class.new_from_sacctmgr(
                    line)
                if not parent:
                    raise(SlurmParserError(
                        'Found user record without Parent for line: {}'.format(line)))
                account = cluster.accounts[parent]
                account.add_user(user)
                cluster.accounts[parent] = account

        if not cluster or not cluster.name:
            raise(SlurmParserError(
                'Failed to parse Slurm cluster name. Is this in sacctmgr dump file format?'))

        return cluster

    @classmethod
    def new_from_resource(SlurmCluster_class, resource, addroot=False):
        """Create a new SlurmCluster from a ColdFront Resource model.

        If addroot is set, will include a root account/user if no children.
        This is to match new_from_stream
        """
        name = resource.get_attribute(SLURM_CLUSTER_ATTRIBUTE_NAME)
        specs = resource.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
        user_specs = resource.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        if not name:
            raise(SlurmError('Resource {} missing slurm_cluster'.format(resource)))

        cluster = SlurmCluster_class(name, specs)

        # Process allocations
        for allocation in resource.allocation_set.filter(status__name='Active'):
            alloc_specs = resource.get_attribute_list(
                SLURM_SPECS_ATTRIBUTE_NAME,
                extra_allocations=[allocation])
            alloc_user_specs = resource.get_attribute_list(
                SLURM_USER_SPECS_ATTRIBUTE_NAME,
                extra_allocations=[allocation])
            cluster.add_allocation(allocation, 
                specs=alloc_specs, user_specs=alloc_user_specs)

        # Process child resources
        children = Resource.objects.filter(
            parent_resource_id=resource.id, resource_type__name='Cluster Partition')
        for r in children:
            for allocation in r.allocation_set.filter(status__name='Active'):
                partition_specs = r.get_attribute_list(
                    SLURM_SPECS_ATTRIBUTE_NAME, extra_allocations=[allocation])
                partition_user_specs = r.get_attribute_list(
                    SLURM_USER_SPECS_ATTRIBUTE_NAME,
                    extra_allocations=[allocation])
                cluster.add_allocation(allocation, specs=partition_specs, user_specs=partition_user_specs)

        if not cluster.accounts:
            # No child accounts, add root if addroot is set
            if addroot:
                rootacct = SlurmCluster_class.SlurmAccount_class('root')
                rootuser = SlurmCluster_class.SlurmUser_class(
                    name='root',
                    specs=ROOT_USER_SPEC_LIST,
                    parent='root',)
                rootacct.add_user(rootuser)
                cluster.accounts['root'] = rootacct
                
        return cluster

    def add_allocation(self, allocation, specs=None, user_specs=None):
        if specs is None:
            specs = []

        """Add accounts from a ColdFront Allocation model to SlurmCluster"""
        name = allocation.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = 'root'

        logger.debug("Adding allocation name=%s specs=%s user_specs=%s", name, specs, user_specs)
        account = self.accounts.get(name, self.SlurmAccount_class(name))

        # Set parent of account from SLURM_ACCOUNT_PARENT_ATTRIBUTE_NAME
        parent_name = allocation.get_attribute(
            'SLURM_ACCOUNT_PARENT_ATTRIBUTE_NAME')
        if not parent_name:
            parent_name = 'root'
        parent_account = None
        if parent_name:
            if parent_name == 'root':
                if 'root' not in self.accounts:
                    self.accounts['root'] = \
                        self.SlurmAccount_class('root')
            parent_account = self.accounts[parent_name]
        if parent_account is not None:
            account.parent = parent_account

        account.add_allocation(allocation, user_specs=user_specs)
        account.specs += specs
        self.accounts[name] = account

    def write(self, out):
        self._write(out, "# ColdFront Allocation Slurm associations dump {}\n".format(
            datetime.datetime.now().date()))
        self._write(out, "Cluster - '{}':{}\n".format(
            self.name,
            self.format_specs(),
        ))
        if 'root' in self.accounts:
            self.accounts['root'].write(out)
        else:
            self._write(out, "Parent - 'root'\n")
            self._write(
                out, "User - 'root':{}\n".format(ROOT_USER_SPEC_STRING))

        # We need to order the accounts so that parents are listed before
        # their children.
        accounts_added = set(['root'])
        accs2add = []
        for name, account in self.accounts.items():
            if account.name == 'root':
                continue
            parent = account.parent
            if parent is None or parent.name in accounts_added:
                # Either no parent, or we already wrote entry for parent
                account.write(out)
                accounts_added.add(name)
            else:
                # Parent not added yet, we defer writing it
                accs2add.append((name, account))
        # Handle deferred accounts
        while accs2add:
            newaccs = accs2add
            accs2add = []
            for name, account in newaccs:
                parent = account.parent
                if parent is None or parent.name in accounts_added:
                    # Safe to add now
                    account.write(out)
                    accounts_added.add(name)
                else:
                    # Still need to defer
                    accs2add.append((name,account))

        for name, account in self.accounts.items():
            account.write_users(out)

    @classmethod
    def update_cluster_to(
        SlurmCluster_class, old, new, flags=[], noop=False, noout=False):
        """Issue Slurm commands to update the cluster old to new.

        If old == None, creates the cluster
        If new == None, deletes the cluster
        Will recursively go through accounts, users, etc.

        If noop is given, do not actually run commands but just print
        (unless noout is set) and return a string listing what commands 
        would be run.

        Flags should be a list of flags controlling behavior.  Any flags
        given will be passed to update_*_to and compare_slurm_specs 
        methods of descendent accounts and users beneath the cluster, 
        and therefore unrecognized flags are ignored.  Typically, flags
        will have an action prefix (e.g. ignore_*, skip_*, force_*),
        followed by a name or name_subname.  All flags default to
        unset.

        Flags recognized by update_cluster_to are:
            skip_create_cluster: if set, do not create cluster
                if missing.  If old cluster is missing, just return.
            skip_delete_cluster: if set, do not delete cluster
                if new is None.  See also force_delete_cluster.
            force_delete_cluster: if new is None, the code _should_
                delete the old cluster, but it will not unless this
                flag is set.  If this flag AND skip_delete_cluster
                are both set, skip_delete_cluster wins (i.e. do not
                delete).  If neither are set, a warning will be
                produced if new is None.
            skip_cluster_specs: if set, do not compare the cluster
                specs.
            ignore_<spec_field>: if set, compare_slurm_specs will
                ignore the value of the spec_field Slurm spec when
                comparing specs.  For set-valued/TRES-valued fields,
                the entire field is ignored.
            ignore_<spec_field>_<subfld>: if set and spec_field is
                TRES-valued, the TRES named <tag> is ignored by 
                compare_slurm_specs for that spec_field.
        """
        output = ''
        if old is None:
            # Old cluster does not exist, so add new cluster
            if new is None:
                # But neither does new, huh?  But not an error
                return output
            if 'skip_create_cluster' in flags:
                logger.info('Not creating cluster {}: '
                    'skip_create_cluster is set'.format(new.name))
                return output

            # Create the cluster
            new_cname = new.name
            new_specs = new.spec_dict_to_list()
            tmpout = slurm_add_cluster(
                cluster=new_cname, 
                specs=new_specs, 
                noop=noop, 
                noout=noout)
            output += tmpout

            # Create the accounts beneath it
            # We need to order the accounts so that parents are done
            # before their children.
            accounts_procd = set()
            accs2proc = []

            for name, account in new.accounts.items():
                parent = account.parent
                if parent is None or parent.name in accounts_procd:
                    # Either no parent, or already handled
                    accounts_procd.add(name)
                    tmpout = account.update_account_to(
                        old=None,
                        new=account,
                        flags=flags,
                        cluster=new.name,
                        noop=noop, 
                        noout=noout)
                    output += tmpout
                else:
                    # Defer processing until after parent
                    accs2proc.append((name, account))
            # Handle deferred accounts
            while accs2proc:
                newaccs = accs2proc
                accs2proc = []
                for name, account in newaccs:
                    parent = account.parent
                    if parent is None or parent.name in accounts_procd:
                        # Parent has been processed
                        accounts_procd.add(name)
                        tmpout = account.update_account_to(
                            old=None,
                            new=account,
                            flags=flags,
                            cluster=new.name,
                            noop=noop, 
                            noout=noout)
                        output += tmpout
                    else:
                        # Still need to defer
                        accs2proc.append((name,account))

            return output
        
        # Old exists
        if new is None:
            # New cluster does not exist, so delete old cluster
            #
            if 'skip_delete_cluster' in flags:
                logger.info('Not deleting cluster {}: '
                    'skip_delete_cluster is set'.format(old.name))
                return output
            if not 'force_delete_cluster' in flags:
                logger.warning('Cowardly refusing to delete cluster {}:'
                    ' force_delete_cluster not set.'.format(old.name))
                return output
            # First delete all of our accounts (which will do users as well)
            # We need to do child accounts first, then parents

            # We need to temporarily remove 'skip_delete_account' flag
            tmpflags = flags
            if 'skip_delete_account' in tmpflags:
                tmpflags.remove('skip_delete_account')

            # Make hash of children by parents
            children_by_parent = {}
            for aname, oldaccount in old.accounts.items():
                parent = oldaccount.parent
                if not parent:
                    continue
                pname = parent.name
                if pname in children_by_parent:
                    children = children_by_parent[pname]
                    children.append(aname)
                else:
                    children_by_parent[pname] = [ aname ]
            
            accs2proc = []
            for aname, oldaccount in old.accounts.items():
                if aname not in children_by_parent:   
                    # Oldaccount is childless or children already processed
                    parent = oldaccount.parent
                    if parent:
                        pname = parent.name
                        if pname in children_by_parent:
                            children = children_by_parent[pname]
                            if aname in children:
                                children.remove(aname)
                            if not children:
                                children_by_parent.pop(pname)
                    if aname == 'root':
                        continue
                    tmpout = oldaccount.update_account_to(
                        old=oldaccount,
                        new=None,
                        flags=tmpflags,
                        cluster=old.name,
                        noop=noop, 
                        noout=noout)
                    output += tmpout
                else:
                    # Defer processing until after all children processed
                    accs2proc.append((aname, oldaccount))
            # Handle deferred accounts
            while accs2proc:
                oldaccs = accs2proc
                accs2proc = []
                for aname, oldaccount in oldaccs:
                    if aname not in children_by_parent:
                        # Oldaccount is childless or children already processed
                        parent = oldaccount.parent
                        if parent:
                            pname = parent.name
                            if pname in children_by_parent:
                                children = children_by_parent[pname]
                                if aname in children:
                                    children.remove(aname)
                                if not children:
                                    children_by_parent.pop(pname)
                        if aname == 'root':
                            continue
                        tmpout = oldaccount.update_account_to(
                            old=oldaccount,
                            new=None,
                            flags=tmpflags,
                            cluster=old.name,
                            noop=noop, 
                            noout=noout)
                        output += tmpout
                    else:
                        # Defer processing until all children processed
                        accs2proc.append((aname, oldaccount))

            # Then delete the cluster
            tmpout = slurm_remove_cluster(cluster=old.name, 
                    noop=noop, noout=noout)
            output += tmpout
            return output

        # Both old and new exist, compare them
        if old.name != new.name:
            raise SlurmError('Cluster name mismatch: old={}, '
                'new={}'.format(old.name, new.name))

        diffs = False
        if not 'skip_cluster_specs' in flags:
            diffs = old.compare_slurm_specs(
                spec2=new.spec_dict(), flags=flags)

        if diffs:
            # Modify the cluster
            tmpout = slurm_modify_cluster(cluster=new.name, specs=diffs, 
                    noop=noop, noout=noout)
            output += tmpout

        # Now compare accounts old vs new

        # Start with accounts in new
        # We need to order the accounts so that parents are done
        # before their children (required for creation of new accounts)
        accounts_procd = set()
        accs2proc = []

        for aname, newaccount in new.accounts.items():
            parent = newaccount.parent
            if parent is None or parent.name in accounts_procd:
                # Either no parent, or already handled
                accounts_procd.add(aname)
                if aname in old.accounts:
                    #Account exists in both old and new
                    oldaccount = old.accounts[aname]
                    tmpout = newaccount.update_account_to(
                        old=oldaccount,
                        new=newaccount,
                        flags=flags,
                        cluster=new.name,
                        noop=noop, 
                        noout=noout)
                    output += tmpout
                else:
                    #Account only exists in new
                    tmpout = newaccount.update_account_to(
                        old=None,
                        new=newaccount,
                        flags=flags,
                        cluster=new.name, 
                        noop=noop, 
                        noout=noout)
                    output += tmpout
            else:
                # Defer processing until after parent
                accs2proc.append((aname, newaccount))
        # Handle deferred accounts
        while accs2proc:
            newaccs = accs2proc
            accs2proc = []
            for aname, newaccount in newaccs:
                parent = newaccount.parent
                if parent is None or parent.name in accounts_procd:
                    # Parent has been processed
                    accounts_procd.add(aname)
                    tmpout = account.update_account_to(
                        old=None,
                        new=newaccount,
                        flags=flags,
                        cluster=new.name,
                        noop=noop, 
                        noout=noout)
                    output += tmpout
                else:
                    # Still need to defer
                    accs2proc.append((aname,newaccount))


        # Now delete accounts only in old 
        # This needs to be done so that child accounts are
        # processed before parents.

        # Make hash of children by parents
        children_by_parent = {}
        for aname, oldaccount in old.accounts.items():
            if aname in new.accounts:
                # Skip accounts in both old and new, handled earlier
                continue
            parent = oldaccount.parent
            if not parent:
                continue
            pname = parent.name
            if pname in children_by_parent:
                children = children_by_parent[pname]
                children.append(aname)
            else:
                children_by_parent[pname] = [ aname ]
        
        accs2proc = []
        for aname, oldaccount in old.accounts.items():
            if aname in new.accounts:
                # Skip accounts in both old and new, handled earlier
                continue
            if aname not in children_by_parent:   
                # Oldaccount is childless or children already processed
                parent = oldaccount.parent
                if parent:
                    pname = parent.name
                    if pname in children_by_parent:
                        children = children_by_parent[pname]
                        if aname in children:
                            children.remove(aname)
                        if not children:
                            children_by_parent.pop(pname)
                if aname == 'root':
                    continue
                tmpout = oldaccount.update_account_to(
                    old=oldaccount,
                    new=None,
                    flags=flags,
                    cluster=old.name,
                    noop=noop, 
                    noout=noout)
                output += tmpout
            else:
                # Defer processing until after all children processed
                accs2proc.append((aname, oldaccount))
        # Handle deferred accounts
        while accs2proc:
            oldaccs = accs2proc
            accs2proc = []
            for aname, oldaccount in oldaccs:
                if aname in new.accounts:
                    # Skip accounts in both old and new, handled earlier
                    continue
                if aname not in children_by_parent:
                    # Oldaccount is childless or children already processed
                    parent = oldaccount.parent
                    if parent:
                        pname = parent.name
                        if pname in children_by_parent:
                            children = children_by_parent[pname]
                            if aname in children:
                                children.remove(aname)
                            if not children:
                                children_by_parent.pop(pname)
                    if aname == 'root':
                        continue
                    tmpout = oldaccount.update_account_to(
                        old=oldaccount,
                        new=None,
                        flags=flags,
                        cluster=old.name,
                        noop=noop, 
                        noout=noout)
                    output += tmpout
                else:
                    # Defer processing until all children processed
                    accs2proc.append((aname, oldaccount))

        return output

