import {
  useMutation,
  useQuery,
  type QueryFunction,
  type QueryKey,
  type UseMutationOptions,
  type UseMutationResult,
  type UseQueryOptions,
  type UseQueryResult,
} from '@tanstack/react-query';
import type { ApiResponse } from '../api/types';

function unwrap<T>(response: ApiResponse<T>): T {
  if (!response.ok) {
    throw new Error(response.error.message);
  }

  return response.data;
}

export function useApiQuery<TData, TQueryKey extends QueryKey = QueryKey>(
  queryKey: TQueryKey,
  fetcher: QueryFunction<ApiResponse<TData>, TQueryKey>,
  options?: Omit<UseQueryOptions<ApiResponse<TData>, Error, TData, TQueryKey>, 'queryKey' | 'queryFn' | 'select'>,
): UseQueryResult<TData, Error> {
  return useQuery({
    queryKey,
    queryFn: fetcher,
    select: unwrap,
    retry: false,
    ...(options ?? {}),
  });
}

export function useApiMutation<TData, TVariables = void>(
  mutationFn: (variables: TVariables) => Promise<ApiResponse<TData>>,
  options?: Omit<UseMutationOptions<TData, Error, TVariables, unknown>, 'mutationFn'>,
): UseMutationResult<TData, Error, TVariables, unknown> {
  return useMutation({
    mutationFn: async (variables: TVariables) => {
      const response = await mutationFn(variables);
      return unwrap(response);
    },
    ...(options ?? {}),
  });
}
