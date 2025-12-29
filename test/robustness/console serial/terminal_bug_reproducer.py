import libs.testium as tm

def RetreiveData(console_name):
    print("--------------- retrieving data ---------------")
    result = 0
    cons   = tm.console(console_name)

    if cons is None:
        print("--------------- The console does not exist ---------------")
    else:
        try:
            is_finished = False
            while not is_finished:
                status, d = cons.read_until('\n', timeout=0, return_data=True, mute=True)
                if 0 == status:
                    print("--------------- Data ---------------")
                    print(d)
                else:
                    print("--------------- No data ---------------")
                    print("Status: ", status)
                    is_finished = True
        except:
            print("--------------- Error retrieving data ---------------")
            result = -1

    return result
