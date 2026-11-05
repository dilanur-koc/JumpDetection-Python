Shader "Radar/ScreenSpotlight2D"
{
    Properties
    {
        _MainTex ("Sprite Texture", 2D) = "white" {}
        [HideInInspector] _Color ("Tint", Color) = (1,1,1,1)
        _SpotCenter ("Light center", Vector) = (0,0,0,0)
        _SpotRadii ("Light radius", Vector) = (7.5,5.5,0,0)
        _Ambient ("Distant surface visibility", Range(0,1)) = 0.025
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Blend SrcAlpha OneMinusSrcAlpha, One OneMinusSrcAlpha
        Cull Off
        ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #include "Packages/com.unity.render-pipelines.universal/Shaders/2D/Include/Core2D.hlsl"
            #pragma vertex Vertex
            #pragma fragment Fragment
            #pragma multi_compile_instancing
            #pragma multi_compile _ DEBUG_DISPLAY SKINNED_SPRITE

            struct Attributes
            {
                COMMON_2D_INPUTS
                half4 color : COLOR;
                UNITY_SKINNED_VERTEX_INPUTS
            };
            struct Varyings
            {
                COMMON_2D_OUTPUTS
                half4 color : COLOR;
                float2 worldPosition : TEXCOORD4;
            };
            #include "Packages/com.unity.render-pipelines.universal/Shaders/2D/Include/2DCommon.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
                float4 _SpotCenter;
                float4 _SpotRadii;
                half _Ambient;
            CBUFFER_END

            Varyings Vertex(Attributes input)
            {
                UNITY_SKINNED_VERTEX_COMPUTE(input);
                SetUpSpriteInstanceProperties();
                input.positionOS = UnityFlipSprite(input.positionOS, unity_SpriteProps.xy);
                Varyings output = CommonUnlitVertex(input);
                output.color = input.color * _Color * unity_SpriteColor;
                output.worldPosition = TransformObjectToWorld(input.positionOS).xy;
                return output;
            }

            half4 Fragment(Varyings input) : SV_Target
            {
                half4 surface = CommonUnlitFragment(input, input.color);
                // Kamera hareket ettikçe merkez güncellenir. Işık ekrandaki yerini korur.
                float2 offset = (input.worldPosition - _SpotCenter.xy) / max(_SpotRadii.xy, 0.01);
                half light = 1 - smoothstep(0.15, 1, length(offset));
                surface.rgb *= lerp(_Ambient, 1, light);
                surface.a *= lerp(0.08, 1, light);
                return surface;
            }
            ENDHLSL
        }
    }
}
