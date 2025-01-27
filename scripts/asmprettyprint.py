import sys

# The widths for the componets of an assembly line
labelWidth = 20-1
opcodeWidth = 10-1
operandWidth = 20-1
commentWidth = 0

# parameters
stripWhitesSpaceAtEnd = True

opcodesWithoutOperands = [
    'abx',
    'asla', 'aslb', 'asld', 'aslq',
    'asra', 'asrb', 'asrd', 'asrq',
    'break',
    'clra', 'clrb', 'clrd', 'comd', 'clre', 'clrf', 'clrw', 'clrq',
    'coma', 'comb', 'comd', 'come', 'comf', 'comw', 'comq',
    'daa',
    'deca', 'decb', 'dece', 'decf', 'decw', 'sync',
    'inca', 'incb', 'incd', 'ince', 'incf', 'incw',
    'log',
    'lsla', 'lslb', 'lsld', 'lsle', 'lslf', 'lslq',
    'lsra', 'lsrb', 'lsrd', 'lsre', 'lsrf', 'lsrq',
    'mul',
    'nega', 'negb', 'negd', 'nege', 'negf', 'negw', 'negq',
    'rti', 'rts',
    'rola', 'rolb', 'rold', 'rolw',
    'rora', 'rorb', 'rord', 'rorw',
    'sex', 'sexw', 'swi', 'swi2', 'swi3',
    'tsta', 'tstb', 'tstd', 'tste', 'tstf', 'tstw', 'tstq',
    # psedu-ops
    'ifp1', 'else', 'endc'
]

opcodesWithOperandsThatCanHaveSpaces = [
    'ttl', 'fcc', 'fcs'
]

def isEmptyLine(l):
    l.strip()
    if len(l) == 0:
        return True
    else:
        return False

def isComment(l):
    if l[0] == '*' or l[0] == ';':
        return True
    else:
        return False

def hasLabel(l):
    result = False
    if len(l) > 0 and not l[0].isspace():
        result = True
    return result

def showLine(label, opcode, operand, comment, debug):
    if debug == True:
        line = [label, opcode, operand, comment]
    else:
        if label == "" and opcode == "" and operand == "":
            line = comment
        else:
            formatString = f"{label:<{labelWidth}} {opcode:<{opcodeWidth}} {operand:<{operandWidth}} {comment:<{commentWidth}}"
            line = formatString
    if stripWhitesSpaceAtEnd == True:
        line = line.rstrip()
    print(line)

def processLine(l):
    line = ""
    label = ""
    opcode = ""
    operand = ""
    comment = ""
    l = l.rstrip('\n')
    if isEmptyLine(l) == True:
        comment = ""
    elif isComment(l) == True:
        comment = l
    else:
        tokens = l.split()
        startIndex = 0
        if hasLabel(l) == True:
            # the next token will be a label
            label = tokens[startIndex]
            startIndex = startIndex + 1
        # the first token will be the opcode
        if len(tokens) > startIndex:
            opcode = tokens[startIndex]
            # if there's a second token AND the first token takes an operand, the second token is an operand
            if len(tokens) > startIndex + 1 and opcode not in opcodesWithoutOperands:
                operand = tokens[startIndex + 1]
                if len(tokens) > startIndex + 2:
                    if opcode in opcodesWithOperandsThatCanHaveSpaces:
                        operand = l.split(None, startIndex + 1)[startIndex + 1]
                    else:
                        comment = l.split(None, startIndex + 2)[startIndex + 2]
                else:
                    comment = ""
            else:
                if len(tokens) > startIndex + 1:
                    comment = l.split(None, startIndex + 1)[startIndex + 1]

    showLine(label, opcode, operand, comment, False)

if len(sys.argv) < 2:
    print("Please provide a filename as an argument.")
    sys.exit(1)

filename = sys.argv[1]

# Using the 'with' statement ensures that the file is properly closed after its suite finishes.
with open(filename, 'r') as file:
    for line in file:
        processLine(line)

