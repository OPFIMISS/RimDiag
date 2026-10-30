using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.Loader;
using HarmonyLib;
using Local.IntegratedVanillaGuards;
using RimWorld;
using Verse;

public static class Program
{
    public static int Main()
    {
        AssemblyLoadContext.Default.Resolving += (_, name) =>
        {
            var path = Path.Combine("D:/Steam/steamapps/common/RimWorld", name.Name + ".dll");
            return File.Exists(path) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(path) : null;
        };
        return Tests.Run();
    }
}

public static class Tests
{
    static int count;
    static void Check(bool pass, string name)
    {
        if (!pass) throw new Exception("FAILED " + name);
        count++;
        Console.WriteLine("PASS " + name);
    }
    static bool Refuses(Action action)
    {
        try { action(); return false; } catch (InvalidOperationException) { return true; }
    }
    public static void MarkerPrefix() { }

    public static int Run()
    {
        // Actual game-reference tests in an offline process, not gameplay or rendering.
        Check(ReadingGuard.IsBook(null) == false, "null type excluded locally");
        foreach (Type type in new[] { typeof(Book), typeof(Thing), typeof(Building), typeof(Pawn), typeof(string) })
            Check(ReadingGuard.IsBook(type) == type.SameOrSubclassOf<Book>(), "normal type equivalent " + type.Name);
        var original = PatchProcessor.GetOriginalInstructions(ReadingGuard.Target).ToList();
        var cloned = original.Select(c => new CodeInstruction(c)).ToList();
        var rewritten = ReadingGuard.Transpiler(cloned).ToList();
        Check(original.Count == rewritten.Count, "reading instruction count preserved");
        Check(original.Zip(rewritten).Count(pair => !Equals(pair.First.operand, pair.Second.operand) || pair.First.opcode != pair.Second.opcode) == 1,
            "only one reading operand changed");
        Check(Refuses(() => ReadingGuard.Transpiler(Array.Empty<CodeInstruction>()).ToList()), "reading absent anchor refused");
        Check(Refuses(() => ReadingGuard.Transpiler(new[] { new CodeInstruction(OpCodes.Call, ReadingGuard.Predicate), new CodeInstruction(OpCodes.Call, ReadingGuard.Predicate) }).ToList()), "reading double anchor refused");

        var smooth = new StuffAppearanceDef { index = 0 };
        var graphic = new Graphic_Single();
        Check(AppearanceGuard.MissingDefault(null, smooth), "null graphics detected");
        Check(AppearanceGuard.MissingDefault(new Graphic[0], smooth), "empty graphics detected");
        Check(AppearanceGuard.MissingDefault(new Graphic[] { null }, smooth), "null default detected");
        Check(AppearanceGuard.MissingDefault(new Graphic[] { graphic }, null), "null appearance detected");
        Check(!AppearanceGuard.MissingDefault(new Graphic[] { graphic }, smooth), "valid default untouched");
        smooth.index = 2;
        Check(AppearanceGuard.MissingDefault(new Graphic[] { graphic }, smooth), "out of range detected");
        AppearanceGuard.ValidateShape(PatchProcessor.GetOriginalInstructions(AppearanceGuard.Target));
        Check(true, "actual vanilla getter shape validated");
        Check(Refuses(() => AppearanceGuard.ValidateShape(new[] { new CodeInstruction(OpCodes.Ret) })), "unknown getter refused");
        var changed = PatchProcessor.GetOriginalInstructions(AppearanceGuard.Target).Select(c => new CodeInstruction(c)).ToList();
        changed.Insert(0, new CodeInstruction(OpCodes.Ldnull));
        Check(Refuses(() => AppearanceGuard.ValidateShape(changed)), "extra getter operation refused");

        var harmony = new Harmony("local.integratedvanillaguards.offline.tests");
        harmony.Patch(ReadingGuard.Target, transpiler: new HarmonyMethod(typeof(ReadingGuard), nameof(ReadingGuard.Transpiler)));
        Check(Harmony.GetPatchInfo(ReadingGuard.Target).Owners.Contains(harmony.Id), "real reading method replacement registered");
        harmony.Patch(AppearanceGuard.Target, prefix: new HarmonyMethod(typeof(AppearanceGuard), nameof(AppearanceGuard.Prefix)));
        Check(Harmony.GetPatchInfo(AppearanceGuard.Target).Owners.Contains(harmony.Id), "real appearance prefix registered");
        harmony.UnpatchAll(harmony.Id);
        Check(Harmony.GetPatchInfo(ReadingGuard.Target)?.Owners.Contains(harmony.Id) != true, "reading cleanup verified");
        Check(Harmony.GetPatchInfo(AppearanceGuard.Target)?.Owners.Contains(harmony.Id) != true, "appearance cleanup verified");
        GuardInstall.ValidateBuild();
        Check(true, "current vanilla fingerprint accepted");
        Check(!(Harmony.GetPatchInfo(ReadingGuard.Target)?.Owners.Contains("local.readingpolicynullguard") == true), "no phantom reading guard");
        var existing = new Harmony("local.readingpolicynullguard");
        existing.Patch(ReadingGuard.Target, prefix: new HarmonyMethod(typeof(Tests), nameof(MarkerPrefix)));
        Check((Harmony.GetPatchInfo(ReadingGuard.Target)?.Owners.Contains("local.readingpolicynullguard") == true), "existing named reading guard identified for delegation");
        existing.UnpatchAll(existing.Id);
        var unknown = new Harmony("local.unknown.offline.test");
        unknown.Patch(ReadingGuard.Target, transpiler: new HarmonyMethod(typeof(ReadingGuard), nameof(ReadingGuard.Transpiler)));
        Check(Refuses(() => GuardInstall.InstallReading(harmony)), "unknown reading transpiler composition refused");
        unknown.Patch(AppearanceGuard.Target, prefix: new HarmonyMethod(typeof(Tests), nameof(MarkerPrefix)));
        Check(Refuses(() => GuardInstall.InstallAppearance(harmony)), "unknown appearance composition refused");
        unknown.UnpatchAll(unknown.Id);
        Console.WriteLine("Checks passed: " + count + ". Actual rendering/BadMat engine initialization not covered.");
        return 0;
    }
}
