def find_place_in_reversed_list(value: int, arr_values, start_index: int) -> int:
    j = start_index
    step = 1
    while j < len(arr_values) and arr_values[j] > value:
        j += step
        if arr_values[j] <= value:
            if step > 1:
                j -= (step - 1)
                step //= 2
        else:
            step = min(2 * step, max(len(arr_values) - j - 1, 1))

    return j


def sorted_list_merge(sorted_lists, inclusion_indicators, start_indices=None):
    """Генератор, эффективно мержит упорядоченные по убыванию списки
        значений с учетом включения/исключения.
       Во всех списках последний элемент "фейковый" (заведомо меньше любого нефейкового значения)
       Первый список должен быть включающим. Например,
       __sorted_lists: [[12, 10, 8, 6, 4, 2, -1], [12, 8, 4, -1], [8, -1]]
       __inclusion_indicators: [True, True, False] (индикаторы включения/исключения)
       должен вернуть значения 12, 4 с соответствующими им индексами
       [0,0,*], [4, 2, _].
       Можно задать начальные индексы в спсиках.

        :param sorted_lists: list[list[object]]
        :param inclusion_indicators: list[bool]
        :param start_indices: list[list[int]]
    """
    cnt_lists = len(inclusion_indicators)
    if start_indices is not None:
        pointers = start_indices
    else:
        pointers = [0] * cnt_lists

    while pointers[0] < len(sorted_lists[0]) - 1:
        main_value = sorted_lists[0][pointers[0]]
        smallest_inclusive_value = main_value
        for pointer_index in range(1, cnt_lists):
            i = find_place_in_reversed_list(main_value, sorted_lists[pointer_index],
                                            pointers[pointer_index])
            pointers[pointer_index] = i
            # если в соответствующем списке нет заданного значения и условие
            # включающее или наоборот, то это значение не подходит
            if inclusion_indicators[pointer_index] != (sorted_lists[pointer_index][i] == main_value):
                if inclusion_indicators[pointer_index]:
                    smallest_inclusive_value = sorted_lists[pointer_index][i]
                break
        else:
            yield main_value, pointers.copy()

        # не забываем двигать указатель в первом списке
        pointers[0] = find_place_in_reversed_list(smallest_inclusive_value, sorted_lists[0],
                                                  pointers[0] + 1)
