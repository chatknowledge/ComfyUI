def split_array_evenly(array, num_parts):
    avg_length = len(array) // num_parts
    split_arrays = []
    for i in range(0, len(array), avg_length):
        split_arrays.append(array[i:i + avg_length])
    return split_arrays


array = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
num_parts = 4-1
split_arrays = split_array_evenly(array, num_parts)
print(split_arrays)
