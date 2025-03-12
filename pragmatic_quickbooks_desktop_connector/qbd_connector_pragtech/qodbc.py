import pyodbc

cn = pyodbc.connect('DSN=QuickBooks Data;')
# print ("-----------------Data",cn)

# cursor = cn.cursor()
# cursor.execute("Update Customer set Name='Sun Rooom' where Name='Sun Room'")
# cursor.execute("SELECT Name FROM Customer")
# for row in cursor.fetchall():
# 	row_as_list = [x for x in row]
# 	if row_as_list[0] == "Sun Rooom":
# 		print(row_as_list)
# #print (type(row))
# cursor.close()
# cn.close() 

# cn = pyodbc.connect('Driver={QODBC Driver for Quickbooks};server=localhost;trusted_connection=Yes;')
cursor1 = cn.cursor()
# print ("Con 1",cn)
cursor1.execute("SELECT isActive, Name, TimeCreated FROM Customer Order by TimeModified asc")
counter = 1
for row in cursor1.fetchall():
#     print("Counter -------------------", counter)
#     print("Data ----------------------", row)
    counter += 1

# cursor.close()
# cn.close()
