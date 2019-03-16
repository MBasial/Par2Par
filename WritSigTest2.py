# Written by M.J. Basial
# Revision 0, 2010 05 29, initial version.
# Revision 1, 2019 03 15, implemented point/nopoint behavior.
#   A Modflow array control record can modify array values if no decimal is present. 
#   E.g. (10F12.4) used to read '12345678' will be seen by Fortran as '1234.5678'.
#   In contrast, (10F12.0) used to read '12345678' will be seen by Fortran as '12345678.'.
#   Also in contrast, (10F12.4) used to read '12345678.' will be seen by Fortran as '12345678.'.
#   It is recommended to always use point=True with Groundwater Vistas because
#   GWV does not end its array control READ records with .0, and therefore will
#   alter the array values if no decimal is present.


def main():
    import sys
    print('WritSigTest: Receives a number as input and prints it out at maximum precision for various field widths.')
    print('Usage: WritSigTest <Value to print>')
    print('')
    # Open input and output files.
    if len(sys.argv) == 2: # The name of the python script is always the first argument
        TestValue = eval(sys.argv[1])
    else:
        print('Incorrect number of input arguments, a value must be provided.')
        quit()
    print('point=True')
    print('            1         2         3         4')
    print('   1234567890123456789012345678901234567890')
    for width in range(1,31):
    	print(str(width).rjust(2) + ' ' + writsig(TestValue, width, point=True) + '|')
    print('   1234567890123456789012345678901234567890')
    print('            1         2         3         4')
    print('   1234567890123456789012345678901234567890')
    for width in range(1,31):
    	print(str(width).rjust(2) + ' ' + writsig(TestValue, width, point=False) + '|')
    print('   1234567890123456789012345678901234567890')
    print('            1         2         3         4')
    print('point=False')
    print('Processing complete.')
    
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

if __name__ == '__main__':
    main()

# debug
#    import pdb
#    pdb.set_trace()
# debug
