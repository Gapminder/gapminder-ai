from google import generativeai

safety_settings_old_categories = [
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_TOXICITY,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_SEXUAL,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_MEDICAL,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_DEROGATORY,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_DANGEROUS,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_VIOLENCE,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
]

safety_settings_new_categories = [
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": generativeai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": generativeai.types.HarmBlockThreshold.BLOCK_NONE,
    },
]
