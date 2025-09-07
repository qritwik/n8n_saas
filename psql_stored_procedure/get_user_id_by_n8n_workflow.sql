CREATE OR REPLACE FUNCTION public.get_user_id_by_n8n_workflow(p_n8n_workflow_id text)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
    result_id BIGINT;
BEGIN
    SELECT user_id INTO result_id
    FROM public.workflows
    WHERE n8n_workflow_id = p_n8n_workflow_id;
    RETURN result_id;
END;
$$;