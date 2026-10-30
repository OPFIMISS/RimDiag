using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Security.Cryptography;
using HarmonyLib;
using RimWorld;
using UnityEngine;
using Verse;

namespace Local.IntegratedVanillaGuards;

// Mod constructors run before Def/icon resolution. Late startup constructors are too late for these icons.
public sealed class GuardMod : Mod
{
    public GuardMod(ModContentPack content) : base(content)
    {
        try
        {
            GuardInstall.ValidateBuild();
            GuardInstall.InstallAppearance(new Harmony(GuardInstall.Owner));
        }
        catch (Exception error)
        {
            new Harmony(GuardInstall.Owner).Unpatch(AppearanceGuard.Target, HarmonyPatchType.All, GuardInstall.Owner);
            Log.Error("[IntegratedVanillaGuards] Appearance installation refused; reading module is independent: " + error);
        }
    }
}

[StaticConstructorOnStartup]
public static class Bootstrap
{
    static Bootstrap()
    {
        try
        {
            GuardInstall.ValidateBuild();
            GuardInstall.InstallReading(new Harmony(GuardInstall.Owner));
        }
        catch (Exception error)
        {
            // Only report install failures; never intercept gameplay exceptions globally.
            new Harmony(GuardInstall.Owner).Unpatch(ReadingGuard.Target, HarmonyPatchType.All, GuardInstall.Owner);
            Log.Error("[IntegratedVanillaGuards] Reading installation refused; appearance module is independent: " + error);
        }
    }
}

public static class GuardInstall
{
    public const string Owner = "local.integratedvanillaguards";
    public const string ExpectedAssemblySha256 = "4E61D57205944C113631234BC55136A1A7C1679667B26008BEE5425BCFFA1463";
    public static void ValidateBuild()
    {
        string actual = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(typeof(Game).Assembly.Location)));
        if (!string.Equals(actual, ExpectedAssemblySha256, StringComparison.Ordinal))
            throw new InvalidOperationException("Unvalidated vanilla build. No protections installed. Expected " + ExpectedAssemblySha256 + "; actual " + actual);
    }

    public static bool InstallReading(Harmony harmony)
    {
        var info = Harmony.GetPatchInfo(ReadingGuard.Target);
        if (info?.Owners.Contains("local.readingpolicynullguard") == true)
        {
            Log.Message("[IntegratedVanillaGuards] Reading protection delegated to existing local.readingpolicynullguard; no duplicate patch.");
            return false;
        }
        if (info?.Transpilers.Any() == true)
            throw new InvalidOperationException("Reading-policy method already has an unknown transpiler; refusing to compose blindly.");
        harmony.Patch(ReadingGuard.Target, prefix: new HarmonyMethod(typeof(ReadingGuard), nameof(ReadingGuard.ReportInvalid)),
            transpiler: new HarmonyMethod(typeof(ReadingGuard), nameof(ReadingGuard.Transpiler)));
        Log.Message("[IntegratedVanillaGuards] Installed local null-type reading predicate. Broken definitions remain broken.");
        return true;
    }

    public static void InstallAppearance(Harmony harmony)
    {
        if (Harmony.GetPatchInfo(AppearanceGuard.Target)?.Owners.Any() == true)
            throw new InvalidOperationException("Appearance getter already patched; refusing unknown composition.");
        AppearanceGuard.ValidateShape(PatchProcessor.GetOriginalInstructions(AppearanceGuard.Target));
        harmony.Patch(AppearanceGuard.Target, prefix: new HarmonyMethod(typeof(AppearanceGuard), nameof(AppearanceGuard.Prefix)));
        Log.Message("[IntegratedVanillaGuards] Installed missing-default-appearance material placeholder; no graphic/Def mutation.");
    }
}

public static class ReadingGuard
{
    public static readonly MethodInfo Target = AccessTools.Method(typeof(ReadingPolicyDatabase), "GenerateStartingPolicies");
    public static readonly MethodInfo Predicate = typeof(GenTypes).GetMethods().Single(m => m.Name == "SameOrSubclassOf"
        && m.IsGenericMethodDefinition && m.GetParameters().Length == 1).MakeGenericMethod(typeof(Book));
    public static readonly MethodInfo Replacement = AccessTools.Method(typeof(ReadingGuard), nameof(IsBook));
    public static bool IsBook(Type type) => type != null && type.SameOrSubclassOf<Book>();
    public static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions)
    {
        var code = instructions.ToList();
        var matches = code.Where(c => c.opcode == OpCodes.Call && Equals(c.operand, Predicate)).ToList();
        if (matches.Count != 1) throw new InvalidOperationException("Expected exactly one Book predicate, got " + matches.Count);
        matches[0].operand = Replacement;
        return code;
    }
    public static void ReportInvalid()
    {
        var invalid = DefDatabase<ThingDef>.AllDefsListForReading.Where(d => d != null && d.thingClass == null).ToList();
        if (invalid.Count != 0)
            Log.Warning("[IntegratedVanillaGuards] Reading policies skip " + invalid.Count + " invalid definitions; missing implementations are NOT repaired: "
                + string.Join(", ", invalid.Take(32).Select(d => d.defName + " [" + (d.modContentPack?.PackageId ?? "unknown") + "]"))
                + (invalid.Count > 32 ? " (list truncated)" : ""));
    }
}

public static class AppearanceGuard
{
    public static readonly MethodInfo Target = AccessTools.PropertyGetter(typeof(Graphic_Appearances), "MatSingle");
    private static readonly HashSet<string> ReportedPaths = new();
    private static int suppressedReports;

    public static bool MissingDefault(Graphic[] graphics, StuffAppearanceDef smooth) =>
        graphics == null || smooth == null || smooth.index < 0 || smooth.index >= graphics.Length || graphics[smooth.index] == null;

    public static void ValidateShape(IEnumerable<CodeInstruction> instructions)
    {
        var code = instructions.Where(c => c.opcode != OpCodes.Nop).ToList();
        var field = AccessTools.Field(typeof(Graphic_Appearances), "subGraphics");
        var smooth = AccessTools.Field(typeof(StuffAppearanceDefOf), "Smooth");
        var index = AccessTools.Field(typeof(Def), "index");
        var material = AccessTools.PropertyGetter(typeof(Graphic), "MatSingle");
        OpCode[] opcodes = { OpCodes.Ldarg_0, OpCodes.Ldfld, OpCodes.Ldsfld, OpCodes.Ldfld, OpCodes.Ldelem_Ref, OpCodes.Callvirt, OpCodes.Ret };
        if (code.Count != opcodes.Length || code.Where((c, i) => c.opcode != opcodes[i]).Any()
            || !Equals(code[1].operand, field) || !Equals(code[2].operand, smooth)
            || !Equals(code[3].operand, index) || !Equals(code[5].operand, material))
            throw new InvalidOperationException("Appearance getter differs from the verified vanilla shape; protection refused.");
    }

    public static bool Prefix(Graphic_Appearances __instance, Graphic[] ___subGraphics, ref Material __result)
    {
        if (!MissingDefault(___subGraphics, StuffAppearanceDefOf.Smooth)) return true;
        // This is only a visibly bad icon/material fallback. It does not restore assets or missing building types.
        __result = BaseContent.BadMat;
        string path = __instance.path ?? "<null>";
        lock (ReportedPaths)
        {
            if (!ReportedPaths.Contains(path))
            {
                if (ReportedPaths.Count < 32)
                {
                    ReportedPaths.Add(path);
                    Log.Warning("[IntegratedVanillaGuards] Missing default appearance for graphic path '" + path
                        + "'; returning vanilla BadMat placeholder for MatSingle only. Asset/Def remains invalid; no package ownership inferred.");
                }
                else if (suppressedReports++ == 0)
                    Log.Warning("[IntegratedVanillaGuards] Further distinct invalid graphic-path reports omitted after 32 entries; placeholder protection continues. Count is not a TPS measurement.");
            }
        }
        return false;
    }
}
