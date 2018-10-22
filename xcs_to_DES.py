with open("/home/rw264/Documents/imageTools-dev/input.txt") as afile:
    contents=afile.readlines()

def xcs_to_des(line):
    #print("0", line)
    if line.find("[[")!=-1:
        start = line.find("[[")
        end =  line.find("]]")
        middle = line.find('|')
        new_line = line[0:start].replace("(","") + " \"" + line[middle+1:end] + "\":"+line[start+2:middle].replace(" ","") +"\n"
        #print("1",new_line)
        line = new_line
    line = line.replace("*",'* ')
    line = line.replace("-->","** ")
    line = line.replace("''' ",'*')
    line = line.replace("'''","*")
    return line
with open("/home/rw264/Documents/imageTools-dev/output.txt","w+") as outfile:
    for line in contents:
        outfile.write(xcs_to_des(line))
