
import baostock
import pandas as pd


def get_day_list(bs: baostock, gp_id, start_date, end_date, str_type, k_type = 'd'):
    ''' 
    获取k线行情数据
    k_type d=日线 w=周线 60=60分钟
    '''
    data_list = []
    list_data = []
    try:
        # Query historical data
        rs = bs.query_history_k_data_plus(
            gp_id, str_type, start_date=start_date, end_date=end_date, frequency=k_type
        )


        while rs.error_code == '0' and rs.next():
            # Fetch one record at a time and append to data_list
            data_list.append(rs.get_row_data())

        # Parse and structure the data into a list of dictionaries
        str_arr = str_type.split(',')
        if len(str_arr) > 1:
            for idx in range(len(data_list)):
                obj = {'Id': idx}
                for i in range(len(str_arr)):
                    obj[str_arr[i]] = data_list[idx][i]
                list_data.append(obj)

        # list_data.reverse() 

        df = pd.DataFrame(list_data)

        return df
    
    except Exception as e:
        print('get_day_list()=>err:'+str(e))
        return []