# Written by M.J. Basial
# Revision 0, 2010 11 07, initial release.
# Revision 1, 2014 11 07, added notes.
# Revision 2, 2019 03 15, updated writsig to Revision 1.

# TODO: Add various kinds of error-checking, file-existence checks, and so on.
# TODO: Improve style to be pythonic.
# TODO: It appears that values of -0.0 can be written improperly as '0000-0.0'.

# Usage note: Two TPL-file delimiters are allowed. 
#             The first behaves in the ordinary PEST fashion.
#             The second gives a full-precision/free-format representation.

def main():
    """This program duplicates the functionality of Doherty's Par2Par, but with Python's greater math functionality."""
    import sys
    import math
    import re
    print("Par2Par: This program duplicates the functionality of Doherty's Par2Par,\n" +
          "         but with Python's greater math functionality.")
    # Open input file.
    if len(sys.argv) == 2: # The name of the python script is always the first argument, so that plus a filenames = 2.
        if sys.argv[1] == "/?":
            print("Usage: Par2Par <Par2Par instruction file>")
            print("Alternate usage: Par2Par (no arguments will result in interactive prompts)")
            quit()
        else:
            try:
                P2PInFile = open(str(sys.argv[1]), "r")
            except IOError:
                print("ERROR: Could not open input file " + sys.argv[1] + "\n")
                quit()
    elif len(sys.argv) == 1: # Use interactive input.
        try:
            P2PInFile = open(input("Name of Par2Par instruction file: "))
        except IOError:
            print("ERROR: Could not open input file " + sys.argv[1] + "\n")
            quit()
    else:
        print("Incorrect number of input arguments, a Par2Par instruction filename must be provided.")
        quit()

    P2PLines = P2PInFile.readlines()
    P2PInFile.close()

    FileList = [] # Add entries to the list as pairs, e.g. [["File1.TPL", "File1.OUT"]]
    PyCode = ""
    sigpoint = True # point/nopoint
    for P2PLine in P2PLines:
    # We identify which section of the input file we're in via the header, and then process accordingly until we reach the next section header.
        if P2PLine.strip() == "* parameter data":
            P2PSection = "parameters"
        elif P2PLine.strip() == "* template and model input files":
            P2PSection = "files"
        elif P2PLine.strip() == "* control data":
            P2PSection = "control"
        else:
            if P2PSection == "parameters":
                # Create a string that is Python-legal, composed of the parameter assignments.
                # Automatically add "_" to beginning of variable names that begin with digits. Par2Par allows digit-first variables, Python does not.
                if P2PLine.lstrip() == "":
                    # Prevents an error caused by attempting to access [0] in a blank line"".
                    pass
                elif P2PLine.lstrip()[0] == "&":
                    PyCode = PyCode[:-1] + " " + P2PLine.lstrip()[1:].lstrip() # Removes leading spaces, ampersand, and leading spaces after the ampersand.
                else:
                    PyCode += P2PLine
            elif P2PSection == "files":
                FileList += [P2PLine.split()]
            elif P2PSection == "control":
                # TODO: Handle this section of the input file; we currently ignore part of it.
                # The "point/nopoint" functionality is important. Modflow array control records can
                # silently add a decimal (e.g. reading with 10F14.6 will assume 6 decimal places.
                # I.E. 12345. != 12345 = 12345e-6 when read with 10F14.6
                if 'nopoint' in P2PLine:
                    sigpoint = False
    # Identify variables that begin with numbers, and prepend "_" to them throughout the PyCode string.
    # Add an additional "_" to variables that begin with an underscore, so that when we strip the underscores,
    # we aren't breaking legitmate variable names.
    # TODO: If we want to be defensive, we could filter out reserved Python keywords. Another option would be to always add "_" to prevent keyword collisions.
    UnderscoreParList = []
    for PyCodeLine in PyCode.split("\n"):
        try:
            if PyCodeLine.lstrip()[0] in "1234567890_":
                UnderscoreParList.append(PyCodeLine.split("=")[0].strip())
        except:
            pass # There is a carriage return at the end that results in a string index error.

    for ParName in UnderscoreParList:
#            PyCode = PyCode.replace(ParName, "_" + ParName)
        PyCode = re.sub(r"\b" + ParName + r"\b", "_" + ParName, PyCode)

    # Um, zowie! I'm kind of thrilled that this next line actually works. The Python authors are genius!
    # That said, it's heavily untested in the Par2Par context. I'll try to keep track of known-to-work cases in comments.
    # Works: simple math (+-*/), max, min, for, if, print, import. Simple functions can be defined.
    # Does not seem to work, reason unclear (calling functions from two imports?):
    # import math
    # import statistics
    # geoSD_Kx2 = statistics.stdev([math.log(k) for k in Kx2_list])
    # WARNING! The exec command permits the execution of arbitrary Python code.
    #     As far as I can tell, a malicious Par2Par input file could use this to do ANYTHING Python allows.
    # TODO: Verify that all Doherty-specified Par2Par functions work. If not, do text replacement of function names so that they do.
    exec(PyCode)

    # Get list of variables used, as dictionary keys, and their values as dictionary entries.
    ParList = dir() # Careful: Need to keep things lower case internally to avoid erroneous failed matches.
    # Remove variable names that are not our Par2Par variables (i.e. Python standard items). This step may not be necessary.
    for Par in ['math', 'sys', 're']:
        ParList.remove(Par)
    ParDict = dict()
    ParDictLC = dict()
    # Keep track of a lower-case version of the variable names, so that comparisons don't fail because of case changes.
    for Par in ParList:
        ParDict[Par] = eval(Par) # Dictionary of parameter names and values
        ParDictLC[Par.lower().lstrip("_")] = Par # Dictionary of lower-case parameter names and unspecified-case parameter names.
                                                 # These are the ones that will be compared to parameter strings in TPL files.
                                                 # Leading "_" are stripped in ParDictLC, to accomodate Par2Par variables that begin with numbers.

    for FileName in FileList:
        # Open input files.
        try:
            InFile = open(FileName[0], "r")
        except IOError:
            print("ERROR: Could not open input file " + FileName[0] + "\n")
            quit()

        # For each parameter file, read it in, and replace each parameter placeholder with a value.
        # Read the template file header.
        try:
            FileText = InFile.readline().strip()
        except IOError:
            print("ERROR: Could not read input file " + FileName[0] + "\n")
            quit()

        # TPL header format check
        # TODO: Add legal-delimiter check.
        # TODO: check line-length math -- if \n is being included, strip it and adjust comparisons?
        if FileText[:3].lower() == "ptf" and len(FileText) > 4:
            Delimiter = FileText[4]
            if len(FileText) >= 6:
                DelimFree = FileText[5]
            else:
                DelimFree = "" # This also evaluates as False.
        else:
            print("ERROR: Bad header format in template file " + FileName[0])
            print("       Correct format is ptf [fixed-width delimiter][free-format delimiter]'")
            print("       Valid delimiters are: TODO")
            print("       Example: 'ptf ~'")
            quit()

        try:
            FileText = InFile.read()
        except IOError:
            print("ERROR: Could not read input file " + FileName[0] + "\n")
            quit()
        # Search and replace all fixed-width-delimited items (standard Par2Par funtionality)
        while True: # We exit the loop with a break statement, so use an always-true condition
            ParStart = FileText.find(Delimiter)
            if ParStart == -1: # No delimiter found.
                break
            ParEnd = ParStart + FileText[ParStart + 1:].find(Delimiter) + 2
            ParLen = ParEnd - ParStart
            ParName = FileText[ParStart + 1:ParEnd - 1].strip()
            ParString = FileText[ParStart:ParEnd]
            ValString = writsig(ParDict[ParDictLC[ParName.lower()]], ParLen, sigpoint)
            FileText = FileText.replace(ParString, ValString)
        # Search and replace all free-format-delimited items
        while DelimFree: # We exit the loop with a break statement, so use an always-true condition (the loop does not start if DelimFree is an empty string)
            ParStart = FileText.find(DelimFree)
            if ParStart == -1: # No delimiter found.
                break
            ParEnd = ParStart + FileText[ParStart + 1:].find(DelimFree) + 2
            ParLen = ParEnd - ParStart
            ParName = FileText[ParStart + 1:ParEnd - 1].strip()
            ParString = FileText[ParStart:ParEnd]
            ValString = repr(ParDict[ParDictLC[ParName.lower()]])
            FileText = FileText.replace(ParString, ValString)

        #Write the output.
        try:
            OutFile = open(FileName[1], "w")
            OutFile.write(FileText)
            print("Template file " + FileName[0] + " used to write\n" +
                  "  output file " + FileName[1])
        except IOError:
            print("ERROR: Could not write output file " + FileName[1] + "\n")
            quit()

    print("Processing complete.")

def writsig(orig_val, orig_width, point=True):
    """Receives a value, a width, and a flag that requires a decimal point.
    Returns a maximum precision representation of that value that will 
    fit in the specified width.
    Width-padding is with leading zeroes."""

    # Written by M.J. Basial
    # Revision 0, 2010 05 29, initial release.
    # Revision 1, 2019 03 15, implemented point/nopoint behavior.
    #   A Modflow array control record can modify array values if no decimal is present. 
    #   E.g. (10F12.4) used to read '12345678' will be seen by Fortran as '1234.5678'.
    #   In contrast, (10F12.0) used to read '12345678' will be seen by Fortran as '12345678.'.
    #   Also in contrast, (10F12.4) used to read '12345678.' will be seen by Fortran as '12345678.'.
    #   It is recommended to always use point=True with Groundwater Vistas because
    #   GWV does not end its array control READ records with .0, and therefore will
    #   alter the array values if no decimal is present.

    # TODO: See if we need to switch back and forth between E+00 and D+00 exponential formats based on precision. I'm not sure if E+00 gets truncated to single precision by ForTran.

    # Reserve space for the - sign, if needed.
    val = orig_val
    width = orig_width
    sign = ''
    if val < 0: # If negative, reserve space for the negative sign
        sign = '-'
        width -= 1
        val = -val

    if len(repr(val)) <= width:
        # If Python's natural representation fits fine, use it.
        result = repr(val)
    else:
        #val_decode is a tool to determine the magnitude of val; we store the magnitude in mantissa.
        val_decode = '{0:>.16E}'.format(val) # 16 places after the decimal to capture double precision and avoid mis-converting things like 0.99999999 as 1.0000E+00
        # mantissa is the exponent (as an integer)
        mantissa = int(val_decode[val_decode.find('E') + 1:])

        if mantissa >= 0: # Positive exponents. The '+' in 1E+5 is optional, but the '-' in 1E-5 is not.
            # We need to figure out if it is better to round to fit the width, or to exponentiate to fit the width.
            if mantissa < width: # Handle via rounding
                # If mantissa = width - 1 or width - 2, round to 0 places and convert to int to drop the '.0' at the end.
                if mantissa == width - 1:
                    result = repr(int(round(val,0)))
                elif mantissa == width - 2:
                    # Add a '.' at the end, so that writsig(12.1, 3) = '12.', not ' 12' (so that an unwanted extra delimiter is avoided)
                    result = repr(int(round(val,0))) + '.'
                else: # Otherwise, round to width - 2 - mantissa
                    result = repr(round(val, width - 2 - mantissa))
            else: # Handle via exponentiation.
                test_width = len(repr(val))
                new_mantissa = 0
                new_val = val
                # Test various exponentiations to achive maximum precision.
                while test_width > width and new_val > 1.0:
                    new_mantissa += 1
                    new_val = val / 10**new_mantissa
                    result = repr(int(round(new_val, 0))) + 'e' + repr(new_mantissa)
                    test_width = len(result)
        else: # Negative exponents.
            if val >= 0.01: # Handle via rounding. Drop leading zeros. Rounding is equivalent to exponentiation when '.00' takes as much space as 'e-3'.
                result = repr(round(val, width - 1))[1:]
            else: # Handle via exponentiation; anything < 0.01 is equal precision or better using exponentiation.
                new_mantissa = mantissa - (width - (len(repr(mantissa)) + 1) - 1)
                new_val = val / 10**mantissa * 10**(width - (len(repr(mantissa)) + 1) - 1)
                result = repr(int(round(new_val, 0))) + 'e' + repr(new_mantissa)
                if len(result) > width: # Handle transitions between e-9 and e-10, e-99 and e-100, etc.
                    result = repr(int(round(new_val/10.0, 0))) + 'e' + repr(new_mantissa + 1)

    # Handle point/nopoint setting
    # point=True - requires a decimal point to be present
    # point=False - means that a decimal point might not be present, but could be present
    if point:
        if '.' not in result:
            # make the field one character narrower and add a decimal if not present
            result = writsig(val, max(width - 1, 1), point=False)
            if '.' not in result:
                if 'e' in result:
                    result = result.replace('e', '.e')
                elif '*' in result:
                    result += '*'
                else:
                    result += '.'

    # Zero-pad on the left when width is greater than the space repr(val) takes.
    if len(result) < width:
        result = '0' * (width - len(result)) + result
    # Add the negative sign back in, if it exists.
    result = sign + result
    # If no legal representation of the number can be fit into the width (e.g. writsig(-1.2e-100,2), return asterisks.
    if len(result) > orig_width:
        result = '*' * orig_width

    return result

if __name__ == "__main__":
    main()

